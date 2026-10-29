from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from fastapi import HTTPException, status

from ..database import responses_collection, surveys_collection
from ..schemas import SurveyCreate


def _now() -> datetime:
    return datetime.now(timezone.utc)


# def survey_doc_to_out(doc: dict, response_count: int = 0) -> dict:
#     return {
#         "id": str(doc["_id"]),
#         "title": doc["title"],
#         "description": doc.get("description", ""),
#         "allow_anonymous": doc.get("allow_anonymous", True),
#         "allow_multiple": doc.get("allow_multiple", False),
#         "questions": doc.get("questions", []),
#         "creator_id": doc["creator_id"],
#         "created_at": doc.get("created_at"),
#         "updated_at": doc.get("updated_at"),
#         "response_count": response_count,
#     }

def survey_doc_to_out(doc: dict, response_count: int = 0) -> dict:
    return {
        "id": str(doc["_id"]),
        "title": doc["title"],
        "description": doc.get("description", ""),
        "allow_anonymous": doc.get("allow_anonymous", True),
        "allow_multiple": doc.get("allow_multiple", False),
        "questions": doc.get("questions", []),
        "creator_id": _to_str_id(doc.get("creator_id")),
        "created_at": doc.get("created_at"),
        "updated_at": doc.get("updated_at"),
        "response_count": response_count,
    }


def create_survey(creator_id: str, payload: SurveyCreate) -> dict:
    now = _now()
    # 题目转成 dict 存库（enum/literal 已经是 str）
    questions = [q.model_dump() for q in payload.questions]

    doc = {
        "creator_id": creator_id,
        "title": payload.title,
        "description": payload.description or "",
        "allow_anonymous": payload.allow_anonymous,
        "allow_multiple": payload.allow_multiple,
        "questions": questions,
        "created_at": now,
        "updated_at": now,
    }
    result = surveys_collection.insert_one(doc)
    doc["_id"] = result.inserted_id
    return survey_doc_to_out(doc)


# def list_surveys_by_creator(creator_id: str) -> list[dict]:
#     docs = list(
#         surveys_collection.find({"creator_id": creator_id}).sort("created_at", -1)
#     )
#     return [survey_doc_to_out(d) for d in docs]

def list_surveys_by_creator(creator_id: str) -> list[dict]:
    oid = ObjectId(creator_id)
    docs = list(
        surveys_collection.find(
            {"$or": [{"creator_id": creator_id}, {"creator_id": oid}]}
        ).sort("created_at", -1)
    )
    return [survey_doc_to_out(d) for d in docs]


def list_all_surveys() -> list[dict]:
    """公开列表：问卷页展示所有问卷。"""
    docs = list(surveys_collection.find({}).sort("created_at", -1))
    # 批量统计回答数，避免 N+1（一次聚合）
    ids = [d["_id"] for d in docs]
    counts: dict[ObjectId, int] = {}
    if ids:
        agg = responses_collection.aggregate(
            [
                {"$match": {"survey_id": {"$in": ids}}},
                {"$group": {"_id": "$survey_id", "cnt": {"$sum": 1}}},
            ]
        )
        counts = {row["_id"]: row["cnt"] for row in agg}
    return [survey_doc_to_out(d, counts.get(d["_id"], 0)) for d in docs]


def get_survey_or_404(survey_id: str) -> dict:
    try:
        oid = ObjectId(survey_id)
    except Exception:
        raise HTTPException(status_code=400, detail="无效的问卷 id")
    doc = surveys_collection.find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="问卷不存在")
    return doc

def _to_str_id(v) -> str | None:
    if v is None:
        return None
    return str(v)

def get_survey_detail(survey_id: str, current_user_id: str | None) -> dict:
    doc = get_survey_or_404(survey_id)
    is_creator = (
        current_user_id is not None
        and _to_str_id(doc.get("creator_id")) == _to_str_id(current_user_id)
    )

    if not doc.get("allow_anonymous", True) and not is_creator:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="该问卷不允许匿名访问",
        )

    count = (
        responses_collection.count_documents({"survey_id": doc["_id"]})
        if is_creator else 0
    )
    return survey_doc_to_out(doc, count)

def delete_survey(survey_id: str, current_user_id: str) -> None:
    """删除问卷及其所有回答。仅创建者可删。"""
    doc = get_survey_or_404(survey_id)
    if _to_str_id(doc.get("creator_id")) != _to_str_id(current_user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有问卷创建者可以删除问卷",
        )
    # 先删回答，再删问卷
    responses_collection.delete_many({"survey_id": doc["_id"]})
    surveys_collection.delete_one({"_id": doc["_id"]})