"""General API response schemas: upload acknowledgement, status, errors."""

from pydantic import BaseModel


class UploadLinks(BaseModel):
    result: str
    status: str


class UploadAccepted(BaseModel):
    message: str
    session_id: str
    upload_id: str
    status: str
    links: UploadLinks


class UploadStatusResponse(BaseModel):
    session_id: str
    upload_id: str
    file_name: str
    file_type: str
    status: str
    current_stage: str
    created_at: str
    updated_at: str
    error_message: str | None = None


class ErrorResponse(BaseModel):
    """Matches BaseResumeException.to_dict() as rendered by the app-level
    exception handler."""

    error_code: str
    message: str
    details: dict = {}
