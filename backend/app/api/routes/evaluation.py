"""AI evaluation endpoint: run the LLM evaluator over a parsed resume."""

from uuid import UUID

from fastapi import APIRouter

from app.api.deps import session_repository
from app.ai.evaluators.panel import PanelEvaluator
from app.ai.evaluators.resume_evaluator import ResumeEvaluator
from app.ai.llm.client import get_llm_provider
from app.core.exceptions import NotFoundError
from app.core.logging import AppLogger
from app.models.resume_document import ResumeDocument
from app.schemas.benchmark_schema import PanelResponse, PersonaVerdict
from app.schemas.jd_schema import EvaluationResponse, to_evaluation_response

router = APIRouter(prefix="/resume", tags=["AI evaluation"])

logger = AppLogger("EvaluationRoute")


@router.post(
    "/{session_id}/{upload_id}/evaluate",
    response_model=EvaluationResponse,
    summary="Run AI evaluation on a parsed resume",
)
async def evaluate_resume(session_id: UUID, upload_id: UUID):
    data = await session_repository.get_extraction(str(session_id), str(upload_id))
    if data is None:
        raise NotFoundError(resource_type="Extraction", resource_id=str(upload_id))

    evaluator = ResumeEvaluator(get_llm_provider())
    evaluation = await evaluator.evaluate(ResumeDocument(**data))

    await session_repository.save_evaluation(
        str(session_id), str(upload_id), evaluation.model_dump(mode="json")
    )
    return to_evaluation_response(str(session_id), str(upload_id), evaluation)


@router.post(
    "/{session_id}/{upload_id}/panel",
    response_model=PanelResponse,
    summary="Run a recruiter / ATS / hiring-manager persona panel on a resume",
)
async def panel_evaluate(session_id: UUID, upload_id: UUID):
    data = await session_repository.get_extraction(str(session_id), str(upload_id))
    if data is None:
        raise NotFoundError(resource_type="Extraction", resource_id=str(upload_id))

    panel = PanelEvaluator(get_llm_provider())
    result = await panel.evaluate(ResumeDocument(**data))
    return PanelResponse(
        session_id=str(session_id),
        upload_id=str(upload_id),
        overall_score=result.overall_score,
        verdicts=[PersonaVerdict(**v.model_dump()) for v in result.verdicts],
        model=result.model,
        prompt_version=result.prompt_version,
    )
