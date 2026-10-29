from datetime import datetime, timezone

from bson import ObjectId
from fastapi import HTTPException, status

from ..database import question_bank_collection
from ..schemas import QuestionBankCreate


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _to_str_id(v):
    return None if v is None else str(v)


def bank_doc_to_out(doc: dict) -> dict:
    return {
        "id": str(doc["_id"]),
        "owner_id": _to_str_id(doc.get("owner_id")),
        "question": doc["question"],
        "name": doc.get("name") or doc["question"].get("title", ""),
        "created_at": doc.get("created_at"),
        "updated_at": doc.get("updated_at"),
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