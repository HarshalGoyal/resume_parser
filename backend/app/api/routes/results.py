"""Read endpoints for retrieving parse results and upload status."""

from uuid import UUID

from fastapi import APIRouter

from app.api.deps import session_repository
from app.core.exceptions import NotFoundError
from app.core.logging import AppLogger
from app.models.resume_document import ResumeDocument
from app.schemas.resume_schema import (
    ResumeExtractionResponse,
    to_extraction_response,
)
from app.schemas.response_schema import UploadStatusResponse

router = APIRouter(prefix="/resume", tags=["Resume results"])

logger = AppLogger("ResumeResults")


@router.get(
    "/{session_id}/{upload_id}",
    response_model=ResumeExtractionResponse,
    summary="Fetch the extracted resume data for an upload",
)
async def get_extraction(session_id: UUID, upload_id: UUID):
    data = await session_repository.get_extraction(str(session_id), str(upload_id))
    if data is None:
        raise NotFoundError(resource_type="Extraction", resource_id=str(upload_id))
    resume = ResumeDocument(**data)
    return to_extraction_response(str(session_id), str(upload_id), resume)


@router.get(
    "/{session_id}/{upload_id}/status",
    response_model=UploadStatusResponse,
    summary="Fetch the processing status of an upload",
)
async def get_status(session_id: UUID, upload_id: UUID):
    metadata = await session_repository.get_upload(str(session_id), str(upload_id))
    if metadata is None:
        raise NotFoundError(resource_type="Upload", resource_id=str(upload_id))
    return UploadStatusResponse(**metadata)
