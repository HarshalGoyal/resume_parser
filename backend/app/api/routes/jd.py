"""JD matching endpoint: compare a parsed resume against a job description."""

from fastapi import APIRouter

from app.api.deps import session_repository
from app.ai.evaluators.jd_matcher import JDMatcher
from app.ai.llm.client import get_llm_provider
from app.core.exceptions import NotFoundError
from app.core.logging import AppLogger
from app.models.resume_document import ResumeDocument
from app.schemas.jd_schema import JDMatchRequest, JDMatchResponse, to_jd_match_response

router = APIRouter(prefix="/jd", tags=["JD matching"])

logger = AppLogger("JDRoute")


@router.post(
    "/match",
    response_model=JDMatchResponse,
    summary="Match a parsed resume against a job description",
)
async def match_jd(request: JDMatchRequest):
    data = await session_repository.get_extraction(
        request.session_id, request.upload_id
    )
    if data is None:
        raise NotFoundError(
            resource_type="Extraction", resource_id=request.upload_id
        )

    matcher = JDMatcher(get_llm_provider())
    result = await matcher.match(ResumeDocument(**data), request.jd_text)
    return to_jd_match_response(request.session_id, request.upload_id, result)
