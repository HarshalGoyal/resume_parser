import asyncio
from datetime import datetime
import uuid

from app.core.logging import AppLogger
from app.models.resume_processing_stages import ResumeProcessingStages
from app.storage.memory_store import MemoryStore
from app.storage.file_store import FileStore
from app.utils.file_utils import safe_stored_filename, sanitize_display_name


logger = AppLogger("SessionRepository")


class SessionRepository:

    def __init__(self):
        logger.info("Initializing SessionRepository")
        self.memory_store: MemoryStore[dict] = MemoryStore()
        self.file_store = FileStore()

    async def create_session(self) -> str:
        session_id = str(uuid.uuid4())
        logger.info(f"Created new session_id={session_id}")
        return session_id

    async def create_upload(
        self,
        session_id: str,
        display_name: str | None,
        file_type: str,
        file_data: bytes,
    ) -> dict:
        upload_id = str(uuid.uuid4())
        logger.info(f"Creating upload_id={upload_id} for session_id={session_id}")

        # Never derive the on-disk path from the client filename (path traversal).
        # Store under a fixed, server-controlled name; keep the original only as
        # display metadata.
        stored_name = safe_stored_filename(file_type)
        original_name = sanitize_display_name(display_name)

        saved_file_path = await asyncio.to_thread(
            self.file_store.save_file,
            session_id=session_id,
            uploaded_file_id=upload_id,
            file_name=stored_name,
            file_data=file_data,
        )
        logger.info(f"Stored upload {upload_id} as {stored_name}")

        metadata = {
            "session_id": session_id,
            "upload_id": upload_id,
            "file_name": original_name,
            "file_type": file_type,
            "saved_file_path": saved_file_path,
            "status": ResumeProcessingStages.UPLOADED.value,
            "current_stage": ResumeProcessingStages.UPLOADED.value,
            "retry_count": 0,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "parsed_text_path": None,
            "evaluation_path": None,
            "error_message": None,
        }

        await self.__persist_metadata(session_id, upload_id, metadata)
        logger.info(f"Upload created successfully upload_id={upload_id}")
        return metadata

    async def get_upload(self, session_id: str, upload_id: str) -> dict | None:
        session_cache = self.memory_store.get(session_id)
        if session_cache and upload_id in session_cache:
            logger.info(f"Cache hit for upload_id={upload_id}")
            return session_cache[upload_id]

        logger.info(f"Cache miss for upload_id={upload_id}")
        try:
            metadata = await asyncio.to_thread(
                self.file_store.read_json,
                session_id=session_id,
                uploaded_file_id=upload_id,
                file_name="metadata.json",
            )
        except FileNotFoundError:
            logger.error(f"Upload metadata not found for upload_id={upload_id}")
            return None

        self.__cache(session_id, upload_id, metadata)
        return metadata

    async def get_extraction(self, session_id: str, upload_id: str) -> dict | None:
        """Read the enriched extraction result (resume_extracted.json), or None
        if the upload doesn't exist or hasn't been parsed yet."""
        try:
            return await asyncio.to_thread(
                self.file_store.read_json,
                session_id=session_id,
                uploaded_file_id=upload_id,
                file_name="resume_extracted.json",
            )
        except FileNotFoundError:
            return None

    async def save_evaluation(
        self, session_id: str, upload_id: str, evaluation: dict
    ) -> None:
        """Persist an AI evaluation next to the upload and record it in the
        upload's metadata (evaluation_path)."""
        await asyncio.to_thread(
            self.file_store.save_json,
            session_id=session_id,
            uploaded_file_id=upload_id,
            file_name="evaluation.json",
            data=evaluation,
        )
        metadata = await self.get_upload(session_id, upload_id)
        if metadata is not None:
            metadata["evaluation_path"] = "evaluation.json"
            metadata["updated_at"] = datetime.now().isoformat()
            await self.__persist_metadata(session_id, upload_id, metadata)

    async def update_stage(
        self, session_id: str, upload_id: str, stage: ResumeProcessingStages
    ) -> dict | None:
        metadata = await self.get_upload(session_id, upload_id)
        if metadata is None:
            return None

        metadata["status"] = stage.value
        metadata["current_stage"] = stage.value
        metadata["updated_at"] = datetime.now().isoformat()

        await self.__persist_metadata(session_id, upload_id, metadata)
        logger.info(f"Updated stage to={stage.value} for upload_id={upload_id}")
        return metadata

    async def mark_failed(
        self, session_id: str, upload_id: str, error_message: str
    ) -> dict | None:
        metadata = await self.get_upload(session_id, upload_id)
        if metadata is None:
            return None

        metadata["status"] = ResumeProcessingStages.FAILED.value
        metadata["current_stage"] = ResumeProcessingStages.FAILED.value
        metadata["error_message"] = error_message
        metadata["retry_count"] += 1
        metadata["updated_at"] = datetime.now().isoformat()

        await self.__persist_metadata(session_id, upload_id, metadata)
        logger.error(f"Marked upload as failed upload_id={upload_id}")
        return metadata

    async def purge_expired(self, ttl_seconds: float) -> int:
        """Metadata lives inside the session directories, which the cleanup
        service removes directly - only the in-memory cache needs clearing so
        deleted sessions don't linger there."""
        self.memory_store = MemoryStore()
        return 0

    async def __persist_metadata(
        self, session_id: str, upload_id: str, metadata: dict
    ) -> None:
        await asyncio.to_thread(
            self.file_store.save_json,
            session_id=session_id,
            uploaded_file_id=upload_id,
            file_name="metadata.json",
            data=metadata,
        )
        self.__cache(session_id, upload_id, metadata)

    def __cache(self, session_id: str, upload_id: str, metadata: dict) -> None:
        """Write-through the per-session in-memory cache (single source of truth
        for the cache-write logic used by create/get/persist)."""
        session_cache = self.memory_store.get(session_id) or {}
        session_cache[upload_id] = metadata
        self.memory_store.set(session_id, session_cache)
