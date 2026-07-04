"""Storage-layer contracts.

SessionRepositoryProtocol is the seam that lets metadata storage move from
JSON files to a database (or anything else) without touching routes/services.
"""

from typing import Protocol

from app.models.resume_processing_stages import ResumeProcessingStages


class SessionRepositoryProtocol(Protocol):
    async def create_session(self) -> str: ...

    async def create_upload(
        self,
        session_id: str,
        display_name: str | None,
        file_type: str,
        file_data: bytes,
    ) -> dict: ...

    async def get_upload(self, session_id: str, upload_id: str) -> dict | None: ...

    async def get_extraction(self, session_id: str, upload_id: str) -> dict | None: ...

    async def save_evaluation(
        self, session_id: str, upload_id: str, evaluation: dict
    ) -> None: ...

    async def update_stage(
        self, session_id: str, upload_id: str, stage: ResumeProcessingStages
    ) -> dict | None: ...

    async def mark_failed(
        self, session_id: str, upload_id: str, error_message: str
    ) -> dict | None: ...

    async def purge_expired(self, ttl_seconds: float) -> int: ...
