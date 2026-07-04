"""SQL-backed session metadata repository (SQLite or Postgres via DATABASE_URL).

Metadata rows live in the database; binary/JSON artifacts (original file,
document_tree.json, resume_extracted.json, evaluation.json) stay on disk via
FileStore - the standard "metadata in DB, blobs on disk" split. Selected by
setting DATABASE_URL (e.g. sqlite+aiosqlite:///sessions.db or
postgresql+asyncpg://user:pass@host/db).
"""

import asyncio
import uuid
from datetime import datetime, timedelta

from sqlalchemy import JSON, DateTime, String, delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core.logging import AppLogger
from app.models.resume_processing_stages import ResumeProcessingStages
from app.storage.file_store import FileStore
from app.utils.file_utils import safe_stored_filename, sanitize_display_name

logger = AppLogger("SQLSessionRepository")


class Base(DeclarativeBase):
    pass


class UploadRow(Base):
    __tablename__ = "uploads"

    session_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    upload_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    data: Mapped[dict] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(DateTime, index=True)


class SQLSessionRepository:
    def __init__(self, database_url: str):
        logger.info("Initializing SQLSessionRepository")
        self.engine = create_async_engine(database_url)
        self.session_factory = async_sessionmaker(self.engine, expire_on_commit=False)
        self.file_store = FileStore()
        self._schema_ready = False
        self._schema_lock = asyncio.Lock()

    async def _ensure_schema(self) -> None:
        if self._schema_ready:
            return
        async with self._schema_lock:
            if self._schema_ready:
                return
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            self._schema_ready = True

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
        await self._ensure_schema()
        upload_id = str(uuid.uuid4())

        stored_name = safe_stored_filename(file_type)
        saved_file_path = await asyncio.to_thread(
            self.file_store.save_file,
            session_id=session_id,
            uploaded_file_id=upload_id,
            file_name=stored_name,
            file_data=file_data,
        )

        now = datetime.now()
        metadata = {
            "session_id": session_id,
            "upload_id": upload_id,
            "file_name": sanitize_display_name(display_name),
            "file_type": file_type,
            "saved_file_path": saved_file_path,
            "status": ResumeProcessingStages.UPLOADED.value,
            "current_stage": ResumeProcessingStages.UPLOADED.value,
            "retry_count": 0,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "parsed_text_path": None,
            "evaluation_path": None,
            "error_message": None,
        }
        async with self.session_factory() as db:
            db.add(
                UploadRow(
                    session_id=session_id,
                    upload_id=upload_id,
                    data=metadata,
                    updated_at=now,
                )
            )
            await db.commit()
        logger.info(f"Upload created upload_id={upload_id}")
        return metadata

    async def get_upload(self, session_id: str, upload_id: str) -> dict | None:
        await self._ensure_schema()
        async with self.session_factory() as db:
            row = await db.get(UploadRow, (session_id, upload_id))
            return row.data if row else None

    async def get_extraction(self, session_id: str, upload_id: str) -> dict | None:
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
        await asyncio.to_thread(
            self.file_store.save_json,
            session_id=session_id,
            uploaded_file_id=upload_id,
            file_name="evaluation.json",
            data=evaluation,
        )
        await self._update(session_id, upload_id, {"evaluation_path": "evaluation.json"})

    async def update_stage(
        self, session_id: str, upload_id: str, stage: ResumeProcessingStages
    ) -> dict | None:
        return await self._update(
            session_id, upload_id,
            {"status": stage.value, "current_stage": stage.value},
        )

    async def mark_failed(
        self, session_id: str, upload_id: str, error_message: str
    ) -> dict | None:
        metadata = await self.get_upload(session_id, upload_id)
        if metadata is None:
            return None
        return await self._update(
            session_id, upload_id,
            {
                "status": ResumeProcessingStages.FAILED.value,
                "current_stage": ResumeProcessingStages.FAILED.value,
                "error_message": error_message,
                "retry_count": metadata["retry_count"] + 1,
            },
        )

    async def purge_expired(self, ttl_seconds: float) -> int:
        await self._ensure_schema()
        cutoff = datetime.now() - timedelta(seconds=ttl_seconds)
        async with self.session_factory() as db:
            result = await db.execute(
                delete(UploadRow).where(UploadRow.updated_at < cutoff)
            )
            await db.commit()
        purged = result.rowcount or 0
        if purged:
            logger.info(f"Purged {purged} expired metadata row(s)")
        return purged

    async def _update(
        self, session_id: str, upload_id: str, changes: dict
    ) -> dict | None:
        await self._ensure_schema()
        now = datetime.now()
        async with self.session_factory() as db:
            row = await db.get(UploadRow, (session_id, upload_id))
            if row is None:
                return None
            data = {**row.data, **changes, "updated_at": now.isoformat()}
            row.data = data
            row.updated_at = now
            await db.commit()
            return data

    async def list_all(self) -> list[dict]:
        """Debug/test helper: all metadata rows."""
        await self._ensure_schema()
        async with self.session_factory() as db:
            rows = (await db.execute(select(UploadRow))).scalars().all()
            return [r.data for r in rows]
