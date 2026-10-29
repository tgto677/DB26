from fastapi import APIRouter, Depends

from ..auth import get_current_user
from ..schemas import QuestionBankCreate, QuestionBankOut
from ..services import question_bank_service

router = APIRouter(prefix="/api/question-bank", tags=["question-bank"])


@router.post("", response_model=QuestionBankOut, status_code=201)
def create_question(
    payload: QuestionBankCreate,
    current_user: dict = Depends(get_current_user),
):
    """保存一道题到我的题目库（需登录）。"""
    return question_bank_service.create_question(str(current_user["_id"]), payload)


@router.get("", response_model=list[QuestionBankOut])
def list_questions(current_user: dict = Depends(get_current_user)):
    """我的题目库列表（需登录）。"""
    return question_bank_service.list_questions(str(current_user["_id"]))


@router.delete("/{qid}", status_code=204)
def delete_question(
    qid: str,
    current_user: dict = Depends(get_current_user),
):
    """删除题目库中的题目（仅本人）。"""
    question_bank_service.delete_question(qid, str(current_user["_id"]))
    return None