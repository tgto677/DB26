from fastapi import APIRouter, Depends

from ..auth import get_current_user
from ..schemas import (
    QuestionBankCreate,
    QuestionBankOut,
    QuestionBankUpdate,
    QuestionBankHistoryItem,
    QuestionBankHistoryDetail,
    QuestionShareRequest,
    QuestionCopyRequest,
    QuestionUsageItem,
    BankQuestionStats
)
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


@router.post("/{qid}/share", response_model=QuestionBankOut, status_code=201)
def share_question(
    qid: str,
    payload: QuestionShareRequest,
    current_user: dict = Depends(get_current_user),
):
    """把自己的题目分享给指定用户名（复制到对方题目库）。"""
    return question_bank_service.share_question(
        qid, str(current_user["_id"]), payload.username
    )


@router.put("/{qid}", response_model=QuestionBankOut)
def update_question(
    qid: str,
    payload: QuestionBankUpdate,
    current_user: dict = Depends(get_current_user),
):
    """修改题目（仅所有者）。修改前自动保存旧版本到历史。"""
    return question_bank_service.update_question(
        qid, str(current_user["_id"]), payload
    )


@router.get("/{qid}/history", response_model=list[QuestionBankHistoryItem])
def list_history(
    qid: str,
    current_user: dict = Depends(get_current_user),
):
    """题目历史版本列表（倒序，仅所有者）。"""
    return question_bank_service.list_history(qid, str(current_user["_id"]))


@router.get("/{qid}/history/{version}", response_model=QuestionBankHistoryDetail)
def get_history_version(
    qid: str,
    version: int,
    current_user: dict = Depends(get_current_user),
):
    """查看某个历史版本的完整内容（仅所有者）。"""
    return question_bank_service.get_history_version(
        qid, str(current_user["_id"]), version
    )


@router.post("/{qid}/restore/{version}", response_model=QuestionBankOut)
def restore_version(
    qid: str,
    version: int,
    current_user: dict = Depends(get_current_user),
):
    """恢复到指定历史版本（仅所有者）。恢复前也会记录当前版本。"""
    return question_bank_service.restore_version(
        qid, str(current_user["_id"]), version
    )

@router.post("/{qid}/copy", response_model=QuestionBankOut, status_code=201)
def copy_question(
    qid: str,
    payload: QuestionCopyRequest | None = None,
    current_user: dict = Depends(get_current_user),
):
    """复制题目为新题目（仅所有者）。副本与原题并存，可独立修改。"""
    return question_bank_service.copy_question(
        qid, str(current_user["_id"]), payload
    )


@router.get("/{qid}/usages", response_model=list[QuestionUsageItem])
def list_usages(
    qid: str,
    current_user: dict = Depends(get_current_user),
):
    """查看该题目被哪些问卷使用（仅所有者）。"""
    return question_bank_service.list_usages(qid, str(current_user["_id"]))


@router.get("/{qid}/stats", response_model=BankQuestionStats)
def bank_question_stats(
    qid: str,
    current_user: dict = Depends(get_current_user),
):
    """跨问卷聚合该题目的统计结果（仅所有者）。"""
    return question_bank_service.bank_question_stats(qid, str(current_user["_id"]))