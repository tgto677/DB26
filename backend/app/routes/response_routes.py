# backend/app/routes/response_routes.py
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from ..auth import _optional_current_user, get_current_user
from ..schemas import ResponseSubmit, SubmitResult, SurveyStats
from ..services import response_service, survey_service, stats_service

router = APIRouter(prefix="/api", tags=["responses"])


@router.post("/surveys/{survey_id}/submit", response_model=SubmitResult)
def submit_survey(
    survey_id: str,
    payload: ResponseSubmit,
    current_user: Optional[dict] = Depends(_optional_current_user),
):
    """
    提交问卷回答。
    - 匿名 / 登录均可（受问卷 allow_anonymous 约束）
    - allow_multiple=False 时登录用户不可重复提交
    """
    survey_doc = survey_service.get_survey_or_404(survey_id)
    user_id = str(current_user["_id"]) if current_user else None
    result = response_service.submit_response(survey_doc, payload, user_id)
    return SubmitResult(message="提交成功", response_id=result["id"])

@router.get("/surveys/{survey_id}/stats", response_model=SurveyStats)
def get_survey_stats(
    survey_id: str,
    current_user: dict = Depends(get_current_user),
):
    """问卷结果统计（仅创建者，需登录）。"""
    survey_doc = survey_service.get_survey_or_404(survey_id)
    if survey_doc["creator_id"] != str(current_user["_id"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有问卷创建者可以查看统计",
        )
    return stats_service.build_survey_stats(survey_doc)