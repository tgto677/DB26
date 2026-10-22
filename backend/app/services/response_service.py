from datetime import datetime, timezone
from typing import Any, Optional

from bson import ObjectId
from fastapi import HTTPException, status

from ..database import responses_collection, surveys_collection
from ..schemas import AnswerItem, ResponseSubmit, ResponseOut, AnswerOut

END = "__end__"


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---------- 跳转引擎 ----------
def _resolve_path(questions: list[dict], answers_map: dict[str, Any]) -> list[str]:
    """
    按题目顺序 + 跳转规则，计算实际被访问到的题目 id 列表。
    answers_map: {question_id: value}
    """
    id_to_index = {q["id"]: i for i, q in enumerate(questions)}
    visited: list[str] = []
    i = 0
    # 防止死循环
    guard = 0
    max_steps = len(questions) * 10 + 10
    while 0 <= i < len(questions):
        guard += 1
        if guard > max_steps:
            raise HTTPException(status_code=400, detail="跳转规则存在循环")
        q = questions[i]
        visited.append(q["id"])

        # 找命中的跳转规则
        target: Optional[str] = None
        hit = False
        for rule in q.get("jump_rules") or []:
            trigger = rule.get("option_value")
            if trigger is None:
                continue
            val = answers_map.get(q["id"])
            if q["type"] == "multiple":
                # 多选：选中值包含 trigger 即命中
                if isinstance(val, list) and trigger in val:
                    hit = True
                    target = rule.get("target_question_id")
                    break
            else:
                # 单选/文本/数字按值匹配（文本/数字题一般不配跳转）
                if val is not None and str(val) == trigger:
                    hit = True
                    target = rule.get("target_question_id")
                    break

        if hit:
            if target is None or target == END:
                break  # 结束问卷
            if target not in id_to_index:
                # 创建时已校验，这里兜底
                raise HTTPException(status_code=400, detail=f"跳转目标不存在: {target}")
            i = id_to_index[target]
        else:
            i += 1

    return visited


# ---------- 单题校验 ----------
def _validate_answer(q: dict, value: Any) -> Any:
    """校验并规范化单题答案。返回规范化后的值。"""
    qtype = q["type"]
    required = q.get("required", False)
    qid = q["id"]

    # 空值判断
    is_empty = value is None or value == "" or value == []
    if is_empty:
        if required:
            raise HTTPException(
                status_code=400, detail=f"题目「{q['title']}」为必填"
            )
        return None

    if qtype == "single":
        if not isinstance(value, str):
            raise HTTPException(status_code=400, detail=f"题目「{q['title']}」应为单值")
        valid = {o["value"] for o in q.get("options", [])}
        if value not in valid:
            raise HTTPException(
                status_code=400, detail=f"题目「{q['title']}」选项不合法"
            )
        return value

    if qtype == "multiple":
        if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
            raise HTTPException(
                status_code=400, detail=f"题目「{q['title']}」应为字符串数组"
            )
        # 去重
        value = list(dict.fromkeys(value))
        valid = {o["value"] for o in q.get("options", [])}
        for v in value:
            if v not in valid:
                raise HTTPException(
                    status_code=400, detail=f"题目「{q['title']}」选项不合法: {v}"
                )
        min_c = q.get("min_choices", 0) or 0
        max_c = q.get("max_choices")
        if len(value) < min_c:
            raise HTTPException(
                status_code=400,
                detail=f"题目「{q['title']}」至少选择 {min_c} 项",
            )
        if max_c is not None and len(value) > max_c:
            raise HTTPException(
                status_code=400,
                detail=f"题目「{q['title']}」最多选择 {max_c} 项",
            )
        return value

    if qtype == "text":
        if not isinstance(value, str):
            raise HTTPException(status_code=400, detail=f"题目「{q['title']}」应为文本")
        min_l = q.get("min_length", 0) or 0
        max_l = q.get("max_length")
        if len(value) < min_l:
            raise HTTPException(
                status_code=400,
                detail=f"题目「{q['title']}」至少 {min_l} 个字符",
            )
        if max_l is not None and len(value) > max_l:
            raise HTTPException(
                status_code=400,
                detail=f"题目「{q['title']}」最多 {max_l} 个字符",
            )
        return value

    if qtype == "number":
        # 接受数字或数字字符串
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            if isinstance(value, str):
                try:
                    value = float(value)
                except ValueError:
                    raise HTTPException(
                        status_code=400, detail=f"题目「{q['title']}」应为数字"
                    )
            else:
                raise HTTPException(
                    status_code=400, detail=f"题目「{q['title']}」应为数字"
                )
        if q.get("integer_only") and float(value) != int(value):
            raise HTTPException(
                status_code=400, detail=f"题目「{q['title']}」必须为整数"
            )
        min_v = q.get("min_value")
        max_v = q.get("max_value")
        if min_v is not None and value < min_v:
            raise HTTPException(
                status_code=400, detail=f"题目「{q['title']}」不能小于 {min_v}"
            )
        if max_v is not None and value > max_v:
            raise HTTPException(
                status_code=400, detail=f"题目「{q['title']}」不能大于 {max_v}"
            )
        return int(value) if q.get("integer_only") else value

    raise HTTPException(status_code=400, detail=f"未知题型: {qtype}")


# ---------- 提交 ----------
def submit_response(
    survey_doc: dict,
    payload: ResponseSubmit,
    current_user_id: Optional[str],
) -> dict:
    survey_id = survey_doc["_id"]
    allow_anonymous = survey_doc.get("allow_anonymous", True)
    allow_multiple = survey_doc.get("allow_multiple", False)

    # 匿名约束
    if current_user_id is None and not allow_anonymous:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="该问卷不允许匿名填写，请先登录",
        )

    # 重复提交约束
    if not allow_multiple:
        if current_user_id is None:
            # 不允许重复但又是匿名：无法可靠识别，直接拒绝
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="该问卷不允许重复填写，请登录后填写",
            )
        exists = responses_collection.find_one(
            {"survey_id": survey_id, "user_id": ObjectId(current_user_id)}
        )
        if exists:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="你已提交过该问卷，不允许重复填写",
            )

    questions = survey_doc.get("questions", [])
    answers_map: dict[str, Any] = {a.question_id: a.value for a in payload.answers}

    # 计算访问路径
    visited = _resolve_path(questions, answers_map)
    visited_set = set(visited)
    q_by_id = {q["id"]: q for q in questions}

    # 校验：只校验被访问到的题
    normalized: list[dict] = []
    for qid in visited:
        q = q_by_id[qid]
        value = answers_map.get(qid)
        norm_val = _validate_answer(q, value)
        if norm_val is None:
            continue
        normalized.append({"question_id": qid, "value": norm_val})

    now = _now()
    doc = {
        "survey_id": survey_id,
        "user_id": ObjectId(current_user_id) if current_user_id else None,
        "is_anonymous": current_user_id is None,
        "answers": normalized,
        "submitted_at": now,
    }
    result = responses_collection.insert_one(doc)

    return {
        "id": str(result.inserted_id),
        "survey_id": str(survey_id),
        "user_id": current_user_id,
        "is_anonymous": current_user_id is None,
        "answers": normalized,
        "submitted_at": now,
    }