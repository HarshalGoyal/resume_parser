"""API schemas for AI evaluation and JD matching."""

from pydantic import BaseModel, Field

from app.models.evaluation import Evaluation
from app.models.jd import JDMatchResult


class EvaluationResponse(BaseModel):
    session_id: str
    upload_id: str
    strengths: list[str]
    weaknesses: list[str]
    ats_score: int
    readability_score: int
    missing_skills: list[str]
    suggestions: list[str]
    prompt_version: str
    model: str


class JDMatchRequest(BaseModel):
    session_id: str
    upload_id: str
    jd_text: str = Field(min_length=30, description="Raw job-description text")


class JDMatchResponse(BaseModel):
    session_id: str
    upload_id: str
    match_percentage: int
    missing_skills: list[str]
    role_alignment: str
    suggestions: list[str]
    prompt_version: str
    model: str


def to_evaluation_response(
    session_id: str, upload_id: str, evaluation: Evaluation
) -> EvaluationResponse:
    data = evaluation.model_dump(exclude={"input_tokens", "output_tokens"})
    return EvaluationResponse(session_id=session_id, upload_id=upload_id, **data)


def to_jd_match_response(
    session_id: str, upload_id: str, result: JDMatchResult
) -> JDMatchResponse:
    data = result.model_dump(exclude={"input_tokens", "output_tokens"})
    return JDMatchResponse(session_id=session_id, upload_id=upload_id, **data)
