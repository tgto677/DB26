from datetime import datetime
from statistics import mean, median
from typing import Any, Optional

from bson import ObjectId

from ..database import responses_collection
from ..schemas import (
    MultipleStat,
    NumberStat,
    OptionStat,
    SingleStat,
    SurveyStats,
    TextStat,
)


def _ratio(count: int, total: int) -> float:
    return round(count / total, 4) if total else 0.0


def build_survey_stats(survey_doc: dict) -> SurveyStats:
    survey_id: ObjectId = survey_doc["_id"]
    questions: list[dict] = survey_doc.get("questions", [])

    # 一次性拉取该问卷所有回答
    docs = list(responses_collection.find({"survey_id": survey_id}))

    total = len(docs)
    anonymous_count = sum(1 for d in docs if d.get("is_anonymous"))
    logged_in_count = total - anonymous_count

    submitted_times = [
        d["submitted_at"] for d in docs if d.get("submitted_at") is not None
    ]
    first_at: Optional[datetime] = min(submitted_times) if submitted_times else None
    last_at: Optional[datetime] = max(submitted_times) if submitted_times else None

    # 按题收集答案： {qid: [value, value, ...]}（只收集非空，提交时已规范化过）
    answers_by_qid: dict[str, list[Any]] = {q["id"]: [] for q in questions}
    for d in docs:
        for ans in d.get("answers", []):
            qid = ans.get("question_id")
            if qid in answers_by_qid:
                answers_by_qid[qid].append(ans.get("value"))

    q_stats: list[Any] = []
    for q in questions:
        qid = q["id"]
        qtype = q["type"]
        values = answers_by_qid.get(qid, [])
        answered = len(values)

        if qtype == "single":
            counts: dict[str, int] = {o["value"]: 0 for o in q.get("options", [])}
            for v in values:
                if v in counts:
                    counts[v] += 1
            options = [
                OptionStat(
                    value=o["value"],
                    label=o["label"],
                    count=counts.get(o["value"], 0),
                    ratio=_ratio(counts.get(o["value"], 0), answered),
                )
                for o in q.get("options", [])
            ]
            q_stats.append(
                SingleStat(question_id=qid, title=q["title"], answered=answered, options=options)
            )

        elif qtype == "multiple":
            counts = {o["value"]: 0 for o in q.get("options", [])}
            total_selected = 0
            for v in values:
                if isinstance(v, list):
                    for item in v:
                        if item in counts:
                            counts[item] += 1
                    total_selected += len(v)
            options = [
                OptionStat(
                    value=o["value"],
                    label=o["label"],
                    count=counts.get(o["value"], 0),
                    ratio=_ratio(counts.get(o["value"], 0), answered),
                )
                for o in q.get("options", [])
            ]
            avg_selected = round(total_selected / answered, 2) if answered else 0.0
            q_stats.append(
                MultipleStat(
                    question_id=qid,
                    title=q["title"],
                    answered=answered,
                    avg_selected=avg_selected,
                    options=options,
                )
            )

        elif qtype == "text":
            texts = [str(v) for v in values if v not in (None, "")]
            q_stats.append(
                TextStat(question_id=qid, title=q["title"], answered=answered, texts=texts)
            )

        elif qtype == "number":
            nums: list[float] = []
            int_count = 0
            non_int_count = 0
            for v in values:
                if isinstance(v, bool) or not isinstance(v, (int, float)):
                    continue
                nums.append(float(v))
                if float(v) == int(v):
                    int_count += 1
                else:
                    non_int_count += 1
            q_stats.append(
                NumberStat(
                    question_id=qid,
                    title=q["title"],
                    answered=len(nums),
                    min=min(nums) if nums else None,
                    max=max(nums) if nums else None,
                    avg=round(mean(nums), 2) if nums else None,
                    median=round(float(median(nums)), 2) if nums else None,
                    integer_count=int_count,
                    non_integer_count=non_int_count,
                )
            )

    return SurveyStats(
        survey_id=str(survey_id),
        title=survey_doc["title"],
        total_responses=total,
        anonymous_count=anonymous_count,
        logged_in_count=logged_in_count,
        first_submitted_at=first_at,
        last_submitted_at=last_at,
        questions=q_stats,
    )