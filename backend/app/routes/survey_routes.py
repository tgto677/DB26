# backend/app/routes/survey_routes.py
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from ..auth import get_current_user, _optional_current_user
from ..schemas import SurveyCreate, SurveyOut, SurveyStats
from ..services import survey_service, stats_service

router = APIRouter(prefix="/api/surveys", tags=["surveys"])


@router.post("", response_model=SurveyOut, status_code=201)
def create_survey(
    payload: SurveyCreate,
    current_user: dict = Depends(get_current_user),
):
    """创建问卷（需登录）。"""
    return survey_service.create_survey(str(current_user["_id"]), payload)


@router.get("/mine", response_model=list[SurveyOut])
def my_surveys(current_user: dict = Depends(get_current_user)):
    """我创建的问卷（需登录）。"""
    return survey_service.list_surveys_by_creator(str(current_user["_id"]))


@router.get("", response_model=list[SurveyOut])
def list_all_surveys():
    """公开问卷列表（无需登录，供 survey 页使用）。"""
    return survey_service.list_all_surveys()


@router.get("/{survey_id}", response_model=SurveyOut)
def get_survey_detail(
    survey_id: str,
    current_user: Optional[dict] = Depends(_optional_current_user),
):
    """
    问卷详情。
    未登录时若问卷 allow_anonymous=False 会 403。
    """
    user_id = str(current_user["_id"]) if current_user else None
    return survey_service.get_survey_detail(survey_id, user_id)


@router.get("/{survey_id}/stats", response_model=SurveyStats)
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