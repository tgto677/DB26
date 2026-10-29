from datetime import datetime
from typing import Any, Literal, Optional, Union

from pydantic import BaseModel, Field, model_validator


# ---------- 用户相关 ----------
class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=30)
    password: str = Field(..., min_length=6, max_length=128)


class UserLogin(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: str
    username: str
    created_at: Optional[datetime] = None


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class MessageOut(BaseModel):
    message: str


# ---------- 题目 ----------
class QuestionOption(BaseModel):
    label: str = Field(..., min_length=1)
    value: str = Field(..., min_length=1)


class JumpRule(BaseModel):
    """跳转规则：选/填了某值 -> 跳到某题；target_question_id 为 None 表示结束。"""
    option_value: Optional[str] = None   # 单/多选按选项 value 触发
    target_question_id: Optional[str] = None


class BaseQuestion(BaseModel):
    id: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    required: bool = False
    jump_rules: list[JumpRule] = Field(default_factory=list)


class SingleQuestion(BaseQuestion):
    type: Literal["single"]
    options: list[QuestionOption] = Field(..., min_length=1)


class MultipleQuestion(BaseQuestion):
    type: Literal["multiple"]
    options: list[QuestionOption] = Field(..., min_length=1)
    min_choices: int = Field(0, ge=0)
    max_choices: Optional[int] = Field(None, ge=1)

    @model_validator(mode="after")
    def check_choices(self):
        if self.max_choices is not None:
            if self.max_choices < self.min_choices:
                raise ValueError("max_choices 不能小于 min_choices")
            if self.max_choices > len(self.options):
                raise ValueError("max_choices 不能超过选项数量")
        return self


class TextQuestion(BaseQuestion):
    type: Literal["text"]
    min_length: int = Field(0, ge=0)
    max_length: Optional[int] = Field(None, ge=1)

    @model_validator(mode="after")
    def check_len(self):
        if self.max_length is not None and self.max_length < self.min_length:
            raise ValueError("max_length 不能小于 min_length")
        return self


class NumberQuestion(BaseQuestion):
    type: Literal["number"]
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    integer_only: bool = False

    @model_validator(mode="after")
    def check_range(self):
        if (
            self.min_value is not None
            and self.max_value is not None
            and self.max_value < self.min_value
        ):
            raise ValueError("max_value 不能小于 min_value")
        return self


Question = Union[SingleQuestion, MultipleQuestion, TextQuestion, NumberQuestion]


# ---------- 题目库 ----------
class QuestionBankCreate(BaseModel):
    question: Question
    name: Optional[str] = None


class QuestionBankOut(BaseModel):
    id: str
    owner_id: str
    question: Question
    name: str
    current_version: int = 1
    copied_from: Optional[str] = None
    shared_from: Optional[str] = None
    shared_from_username: Optional[str] = None
    shared_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class QuestionShareRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=30)


class QuestionCopyRequest(BaseModel):
    name: Optional[str] = None


# ---------- 题目库修改与历史 ----------
class QuestionBankUpdate(BaseModel):
    question: Question
    name: Optional[str] = None


class QuestionBankHistoryItem(BaseModel):
    version: int
    action: str
    name: str
    question_type: str
    title: str
    created_at: Optional[datetime] = None


class QuestionBankHistoryDetail(BaseModel):
    version: int
    action: str
    name: str
    question: Question
    created_at: Optional[datetime] = None


# ---------- 问卷 ----------
class SurveyCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = ""
    allow_anonymous: bool = True
    allow_multiple: bool = False
    questions: list[Question] = Field(..., min_length=1)

    @model_validator(mode="after")
    def validate_questions(self):
        ids = [q.id for q in self.questions]
        if len(ids) != len(set(ids)):
            raise ValueError("题目 id 不能重复")
        id_set = set(ids)
        # 校验跳转目标存在
        for q in self.questions:
            for rule in q.jump_rules:
                if rule.target_question_id and rule.target_question_id not in id_set:
                    raise ValueError(
                        f"题目 {q.id} 的跳转目标 {rule.target_question_id} 不存在"
                    )
        return self


class SurveyOut(BaseModel):
    id: str
    title: str
    description: Optional[str] = ""
    allow_anonymous: bool = True
    allow_multiple: bool = False
    questions: list[Question] = []
    creator_id: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    response_count: int = 0

# ---------- 回答提交 ----------
class AnswerItem(BaseModel):
    question_id: str
    # 单选: str | 多选: list[str] | 文本: str | 数字: float/int
    value: Union[str, float, int, list[str], None] = None


class ResponseSubmit(BaseModel):
    answers: list[AnswerItem] = Field(default_factory=list)


class AnswerOut(BaseModel):
    question_id: str
    value: Union[str, float, int, list[str], None] = None


class ResponseOut(BaseModel):
    id: str
    survey_id: str
    user_id: Optional[str] = None
    is_anonymous: bool = False
    answers: list[AnswerOut] = []
    submitted_at: Optional[datetime] = None


class SubmitResult(BaseModel):
    message: str
    response_id: str

# ---------- 结果统计 ----------
class OptionStat(BaseModel):
    value: str
    label: str
    count: int
    ratio: float          # 占该题回答人数的比例（0~1）


class SingleStat(BaseModel):
    question_id: str
    title: str
    type: Literal["single"] = "single"
    answered: int                     # 回答该题人数
    options: list[OptionStat] = []


class MultipleStat(BaseModel):
    question_id: str
    title: str
    type: Literal["multiple"] = "multiple"
    answered: int
    avg_selected: float = 0.0         # 人均选择数
    options: list[OptionStat] = []


class TextStat(BaseModel):
    question_id: str
    title: str
    type: Literal["text"] = "text"
    answered: int
    texts: list[str] = []


class NumberStat(BaseModel):
    question_id: str
    title: str
    type: Literal["number"] = "number"
    answered: int
    min: Optional[float] = None
    max: Optional[float] = None
    avg: Optional[float] = None
    median: Optional[float] = None
    integer_count: int = 0
    non_integer_count: int = 0


class SurveyStats(BaseModel):
    survey_id: str
    title: str
    total_responses: int
    anonymous_count: int
    logged_in_count: int
    first_submitted_at: Optional[datetime] = None
    last_submitted_at: Optional[datetime] = None
    questions: list[Union[SingleStat, MultipleStat, TextStat, NumberStat]] = []