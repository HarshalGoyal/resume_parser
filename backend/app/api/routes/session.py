from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from uuid import uuid4
from app.models.resume_processing_stages import ResumeProcessingStages

class Session(BaseModel):
    session_id: str = str(uuid4())
    created_at: datetime
    expires_at: Optional[datetime] = None
    user_id: Optional[str] = None
    uploaded_file_id: Optional[str] = None
    status : ResumeProcessingStages = ResumeProcessingStages.NONE
    retry_count: int = 0
