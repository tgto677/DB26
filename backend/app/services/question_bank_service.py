from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from fastapi import HTTPException, status

from ..database import question_bank_collection, question_bank_history_collection, users_collection, responses_collection, surveys_collection
from ..schemas import QuestionBankCreate, QuestionBankUpdate, QuestionCopyRequest


def _save_history(question_oid, owner_id, question, name, action, version):
    question_bank_history_collection.insert_one({
        "question_id": question_oid,
        "owner_id": owner_id,
        "question": question,
        "name": name,
        "version": version,
        "action": action,
        "created_at": _now(),
    })


def _to_str_id(v):
    return None if v is None else str(v)


def _parse_oid(qid: str) -> ObjectId:
    try:
        return ObjectId(qid)
    except Exception:
        raise HTTPException(status_code=400, detail="无效的题目 id")
    

def _ratio(c: int, total: int) -> float:
    return round(c / total, 4) if total else 0.0


def _empty_stat(qtype: str, question: dict):
    if qtype == "single":
        return BankSingleStat(options=[])
    if qtype == "multiple":
        return BankMultipleStat(options=[])
    if qtype == "text":
        return BankTextStat(texts=[])
    return BankNumberStat()


def _aggregate_by_type(qtype: str, question: dict, values: list):
    if qtype == "single":
        # 以题目库当前 options 为基准，额外 value 追加
        label_map = {o["value"]: o["label"] for o in question.get("options", [])}
        counts: dict[str, int] = {v: 0 for v in label_map}
        for v in values:
            if isinstance(v, str):
                counts[v] = counts.get(v, 0) + 1
        total = len([v for v in values if isinstance(v, str)])
        options = [
            BankOptionStat(
                value=v,
                label=label_map.get(v, v),
                count=counts[v],
                ratio=_ratio(counts[v], total),
            )
            for v in counts
        ]
        return BankSingleStat(options=options)

    if qtype == "multiple":
        label_map = {o["value"]: o["label"] for o in question.get("options", [])}
        counts: dict[str, int] = {v: 0 for v in label_map}
        answered = 0
        total_selected = 0
        for v in values:
            if isinstance(v, list):
                answered += 1
                for item in v:
                    counts[item] = counts.get(item, 0) + 1
                    total_selected += 1
        options = [
            BankOptionStat(
                value=v,
                label=label_map.get(v, v),
                count=counts[v],
                ratio=_ratio(counts[v], answered),
            )
            for v in counts
        ]
        avg = round(total_selected / answered, 2) if answered else 0.0
        return BankMultipleStat(avg_selected=avg, options=options)

    if qtype == "text":
        texts = [str(v) for v in values if isinstance(v, str) and v.strip()]
        return BankTextStat(texts=texts)

    # number
    nums = []
    int_count = non_int_count = 0
    for v in values:
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            continue
        nums.append(float(v))
        if float(v) == int(v):
            int_count += 1
        else:
            non_int_count += 1
    return BankNumberStat(
        min=min(nums) if nums else None,
        max=max(nums) if nums else None,
        avg=round(mean(nums), 2) if nums else None,
        median=round(float(median(nums)), 2) if nums else None,
        integer_count=int_count,
        non_integer_count=non_int_count,
    )


def create_question(owner_id: str, payload: QuestionBankCreate) -> dict:
    now = _now()
    q = payload.question.model_dump()
    name = (payload.name or q.get("title") or "").strip() or q.get("title", "")
    doc = {
        "owner_id": owner_id,
        "question": q,
        "name": name,
        "current_version": 1,
        "created_at": now,
        "updated_at": now,
    }
    result = question_bank_collection.insert_one(doc)
    doc["_id"] = result.inserted_id
    _save_history(result.inserted_id, owner_id, q, name, "create", 1)
    return bank_doc_to_out(doc)
def _now() -> datetime:
    return datetime.now(timezone.utc)


def bank_doc_to_out(doc: dict) -> dict:
    return {
        "id": str(doc["_id"]),
        "owner_id": _to_str_id(doc.get("owner_id")),
        "question": doc["question"],
        "name": doc.get("name") or doc["question"].get("title", ""),
        "shared_from": _to_str_id(doc.get("shared_from")),
        "shared_from_username": doc.get("shared_from_username"),
        "shared_at": doc.get("shared_at"),
        "created_at": doc.get("created_at"),
        "updated_at": doc.get("updated_at"),
        "current_version": doc.get("current_version", 1),
        "copied_from": _to_str_id(doc.get("copied_from")),
    }


def create_question(owner_id: str, payload: QuestionBankCreate) -> dict:
    now = _now()
    q = payload.question.model_dump()
    doc = {
        "owner_id": owner_id,
        "question": q,
        "name": (payload.name or q.get("title") or "").strip() or q.get("title", ""),
        "created_at": now,
        "updated_at": now,
    }
    result = question_bank_collection.insert_one(doc)
    doc["_id"] = result.inserted_id
    return bank_doc_to_out(doc)


def list_questions(owner_id: str) -> list[dict]:
    docs = list(
        question_bank_collection.find({"owner_id": owner_id}).sort("created_at", -1)
    )
    return [bank_doc_to_out(d) for d in docs]


def delete_question(qid: str, owner_id: str) -> None:
    try:
        oid = ObjectId(qid)
    except Exception:
        raise HTTPException(status_code=400, detail="无效的题目 id")
    doc = question_bank_collection.find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="题目不存在")
    if _to_str_id(doc.get("owner_id")) != _to_str_id(owner_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只能删除自己的题目",
        )
    question_bank_collection.delete_one({"_id": oid})


def share_question(qid: str, owner_id: str, target_username: str) -> dict:
    """
    把题目库中的某题复制分享给目标用户。
    - 仅题目所有者可分享
    - 目标用户必须存在
    - 不能分享给自己
    - 重复分享（同一题分享给同一人多次）允许，产生多份副本；如需去重可加判断
    """
    # 1. 校验题目存在且属于 owner
    try:
        oid = ObjectId(qid)
    except Exception:
        raise HTTPException(status_code=400, detail="无效的题目 id")

    doc = question_bank_collection.find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="题目不存在")
    if _to_str_id(doc.get("owner_id")) != _to_str_id(owner_id):
        raise HTTPException(status_code=403, detail="只能分享自己的题目")

    # 2. 校验目标用户
    target = users_collection.find_one({"username": target_username})
    if not target:
        raise HTTPException(status_code=404, detail="目标用户不存在")
    if _to_str_id(target["_id"]) == _to_str_id(owner_id):
        raise HTTPException(status_code=400, detail="不能分享给自己")

    # 3. 获取分享者用户名（用于展示）
    owner = users_collection.find_one({"_id": ObjectId(owner_id)})
    owner_username = owner["username"] if owner else ""

    # 4. 复制一份到目标用户题目库
    now = _now()
    new_doc = {
        "owner_id": _to_str_id(target["_id"]),
        "question": doc["question"],
        "name": doc.get("name") or doc["question"].get("title", ""),
        "current_version": 1,
        "shared_from": _to_str_id(owner_id),
        "shared_from_username": owner_username,
        "shared_at": now,
        "created_at": now,
        "updated_at": now,
    }
    result = question_bank_collection.insert_one(new_doc)
    _save_history(
        result.inserted_id,
        _to_str_id(target["_id"]),
        doc["question"],
        new_doc["name"],
        "create",
        1,
    )
    new_doc["_id"] = result.inserted_id
    return bank_doc_to_out(new_doc)


def update_question(qid: str, owner_id: str, payload: QuestionBankUpdate) -> dict:
    try:
        oid = ObjectId(qid)
    except Exception:
        raise HTTPException(status_code=400, detail="无效的题目 id")

    doc = question_bank_collection.find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="题目不存在")
    if _to_str_id(doc.get("owner_id")) != _to_str_id(owner_id):
        raise HTTPException(status_code=403, detail="只能修改自己的题目")

    new_q = payload.question.model_dump()
    new_name = (payload.name or new_q.get("title") or "").strip() or new_q.get("title", "")

    cur_ver = doc.get("current_version", 1)
    # 修改前：把“当前版本”写入历史（若历史中尚无该版本，补一条 update 快照）
    exists = question_bank_history_collection.find_one(
        {"question_id": oid, "version": cur_ver}
    )
    if not exists:
        _save_history(oid, owner_id, doc["question"], doc.get("name", ""), "update", cur_ver)

    next_ver = cur_ver + 1
    question_bank_collection.update_one(
        {"_id": oid},
        {
            "$set": {
                "question": new_q,
                "name": new_name,
                "current_version": next_ver,
                "updated_at": _now(),
            }
        },
    )
    _save_history(oid, owner_id, new_q, new_name, "update", next_ver)

    updated = question_bank_collection.find_one({"_id": oid})
    return bank_doc_to_out(updated)


def list_history(qid: str, owner_id: str) -> list[dict]:
    oid = _parse_oid(qid)
    doc = question_bank_collection.find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="题目不存在")
    if _to_str_id(doc.get("owner_id")) != _to_str_id(owner_id):
        raise HTTPException(status_code=403, detail="只能查看自己题目的历史")

    items = list(
        question_bank_history_collection.find({"question_id": oid}).sort("version", -1)
    )
    return [
        {
            "version": it["version"],
            "action": it.get("action", "update"),
            "name": it.get("name", ""),
            "question_type": it.get("question", {}).get("type", ""),
            "title": it.get("question", {}).get("title", ""),
            "created_at": it.get("created_at"),
        }
        for it in items
    ]


def get_history_version(qid: str, owner_id: str, version: int) -> dict:
    oid = _parse_oid(qid)
    doc = question_bank_collection.find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="题目不存在")
    if _to_str_id(doc.get("owner_id")) != _to_str_id(owner_id):
        raise HTTPException(status_code=403, detail="只能查看自己题目的历史")

    it = question_bank_history_collection.find_one(
        {"question_id": oid, "version": version}
    )
    if not it:
        raise HTTPException(status_code=404, detail="该版本不存在")
    return {
        "version": it["version"],
        "action": it.get("action", "update"),
        "name": it.get("name", ""),
        "question": it["question"],
        "created_at": it.get("created_at"),
    }


def restore_version(qid: str, owner_id: str, version: int) -> dict:
    oid = _parse_oid(qid)
    doc = question_bank_collection.find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="题目不存在")
    if _to_str_id(doc.get("owner_id")) != _to_str_id(owner_id):
        raise HTTPException(status_code=403, detail="只能恢复自己的题目")

    target = question_bank_history_collection.find_one(
        {"question_id": oid, "version": version}
    )
    if not target:
        raise HTTPException(status_code=404, detail="该版本不存在")

    cur_ver = doc.get("current_version", 1)
    # 恢复前：把当前版本快照入历史（action=restore，便于再撤销）
    exists = question_bank_history_collection.find_one(
        {"question_id": oid, "version": cur_ver}
    )
    if not exists:
        _save_history(oid, owner_id, doc["question"], doc.get("name", ""), "restore", cur_ver)

    next_ver = cur_ver + 1
    question_bank_collection.update_one(
        {"_id": oid},
        {
            "$set": {
                "question": target["question"],
                "name": target.get("name", ""),
                "current_version": next_ver,
                "updated_at": _now(),
            }
        },
    )
    _save_history(
        oid, owner_id, target["question"], target.get("name", ""), "restore", next_ver
    )
    updated = question_bank_collection.find_one({"_id": oid})
    return bank_doc_to_out(updated)


def copy_question(qid: str, owner_id: str, payload: Optional[QuestionCopyRequest] = None) -> dict:
    """把题目库中的某题复制为一道新题目（同一所有者），副本与原题并存。"""
    oid = _parse_oid(qid)
    src = question_bank_collection.find_one({"_id": oid})
    if not src:
        raise HTTPException(status_code=404, detail="题目不存在")
    if _to_str_id(src.get("owner_id")) != _to_str_id(owner_id):
        raise HTTPException(status_code=403, detail="只能复制自己的题目")

    base_name = src.get("name") or src["question"].get("title", "")
    new_name = (payload.name.strip() if payload and payload.name and payload.name.strip()
                else f"{base_name}（副本）")

    now = _now()
    doc = {
        "owner_id": _to_str_id(owner_id),
        "question": src["question"],
        "name": new_name,
        "current_version": 1,
        "copied_from": _to_str_id(src["_id"]),
        "created_at": now,
        "updated_at": now,
    }
    result = question_bank_collection.insert_one(doc)
    doc["_id"] = result.inserted_id
    _save_history(result.inserted_id, owner_id, src["question"], new_name, "create", 1)
    return bank_doc_to_out(doc)


def list_usages(qid: str, owner_id: str) -> list[dict]:
    """列出使用该题目库题目的问卷（仅题目所有者可查）。"""
    oid = _parse_oid(qid)
    doc = question_bank_collection.find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="题目不存在")
    if _to_str_id(doc.get("owner_id")) != _to_str_id(owner_id):
        raise HTTPException(status_code=403, detail="只能查看自己题目的使用情况")

    bank_id = str(oid)
    # 查该用户创建、且某题 source_bank_id == bank_id 的问卷
    surveys = list(
        surveys_collection.find(
            {
                "creator_id": _to_str_id(owner_id),
                "questions.source_bank_id": bank_id,
            }
        ).sort("created_at", -1)
    )
    if not surveys:
        return []

    # 批量统计回答数
    sids = [s["_id"] for s in surveys]
    counts = {}
    agg = responses_collection.aggregate(
        [
            {"$match": {"survey_id": {"$in": sids}}},
            {"$group": {"_id": "$survey_id", "cnt": {"$sum": 1}}},
        ]
    )
    for row in agg:
        counts[row["_id"]] = row["cnt"]

    result = []
    for s in surveys:
        # 找到该问卷中使用该题的具体题目 id（可能被复制多次，取第一个/全部）
        for q in s.get("questions", []):
            if q.get("source_bank_id") == bank_id:
                result.append(
                    {
                        "survey_id": str(s["_id"]),
                        "survey_title": s.get("title", ""),
                        "question_id": q.get("id"),
                        "created_at": s.get("created_at"),
                        "response_count": counts.get(s["_id"], 0),
                    }
                )
    return result


from statistics import mean, median
from ..database import responses_collection, surveys_collection
from ..schemas import (
    BankOptionStat, BankSingleStat, BankMultipleStat,
    BankTextStat, BankNumberStat, BankSurveyUsage, BankQuestionStats,
)


def bank_question_stats(qid: str, owner_id: str) -> dict:
    oid = _parse_oid(qid)
    bank_doc = question_bank_collection.find_one({"_id": oid})
    if not bank_doc:
        raise HTTPException(status_code=404, detail="题目不存在")
    if _to_str_id(bank_doc.get("owner_id")) != _to_str_id(owner_id):
        raise HTTPException(status_code=403, detail="只能查看自己题目的统计")

    bank_id = str(oid)
    bank_question = bank_doc["question"]
    qtype = bank_question.get("type")

    # 1. 找到所有使用该题的问卷（当前用户创建）
    surveys = list(
        surveys_collection.find({
            "creator_id": _to_str_id(owner_id),
            "questions.source_bank_id": bank_id,
        })
    )
    survey_ids = [s["_id"] for s in surveys]
    if not survey_ids:
        # 没被使用：返回空统计
        empty = _empty_stat(qtype, bank_question)
        return BankQuestionStats(
            bank_id=bank_id,
            name=bank_doc.get("name") or bank_question.get("title", ""),
            question=bank_question,
            survey_count=0,
            total_responses=0,
            answered=0,
            stat=empty,
            by_survey=[],
        ).model_dump()

    # 2. 拉取这些问卷的回答
    docs = list(responses_collection.find({"survey_id": {"$in": survey_ids}}))

    # 每份问卷里，该题对应的 question_id 集合（可能多个）
    qid_by_survey: dict[ObjectId, set[str]] = {}
    for s in surveys:
        s_qids = {
            q["id"] for q in s.get("questions", [])
            if q.get("source_bank_id") == bank_id
        }
        qid_by_survey[s["_id"]] = s_qids

    # 3. 收集所有该题答案，并按问卷统计回答数
    values: list = []
    answered_per_survey: dict[ObjectId, int] = {sid: 0 for sid in survey_ids}
    total_responses_per_survey: dict[ObjectId, int] = {sid: 0 for sid in survey_ids}

    for d in docs:
        sid = d["survey_id"]
        if sid in total_responses_per_survey:
            total_responses_per_survey[sid] += 1
        s_qids = qid_by_survey.get(sid, set())
        if not s_qids:
            continue
        got = False
        for ans in d.get("answers", []):
            if ans.get("question_id") in s_qids:
                values.append(ans.get("value"))
                got = True
        if got:
            answered_per_survey[sid] += 1

    # 4. 按题型聚合
    stat = _aggregate_by_type(qtype, bank_question, values)

    # 5. 组装 by_survey
    by_survey = []
    title_map = {s["_id"]: s.get("title", "") for s in surveys}
    for sid in survey_ids:
        by_survey.append(BankSurveyUsage(
            survey_id=str(sid),
            survey_title=title_map.get(sid, ""),
            response_count=total_responses_per_survey.get(sid, 0),
            answered=answered_per_survey.get(sid, 0),
        ))

    total_responses = sum(total_responses_per_survey.values())

    return BankQuestionStats(
        bank_id=bank_id,
        name=bank_doc.get("name") or bank_question.get("title", ""),
        question=bank_question,
        survey_count=len(surveys),
        total_responses=total_responses,
        answered=sum(answered_per_survey.values()),
        stat=stat,
        by_survey=by_survey,
    ).model_dump()