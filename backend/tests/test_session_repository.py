"""Tests for SessionRepository: cache-aside behaviour and safe file storage."""

import asyncio
from pathlib import Path

import pytest

from app.storage.session_repository import SessionRepository


@pytest.fixture()
def repo():
    return SessionRepository()


def test_create_upload_persists_and_is_readable(repo):
    async def flow():
        session_id = await repo.create_session()
        meta = await repo.create_upload(
            session_id=session_id,
            display_name="my resume.pdf",
            file_type="pdf",
            file_data=b"%PDF-1.7 test",
        )
        fetched = await repo.get_upload(session_id, meta["upload_id"])
        return meta, fetched

    meta, fetched = asyncio.run(flow())
    assert fetched == meta
    assert meta["file_type"] == "pdf"
    saved = Path(meta["saved_file_path"])
    assert saved.is_absolute()
    assert saved.exists()
    assert saved.name == "original.pdf"


def test_client_filename_never_reaches_disk_path(repo):
    """A hostile client filename must not influence where the file is written."""

    async def flow():
        session_id = await repo.create_session()
        return await repo.create_upload(
            session_id=session_id,
            display_name="../../../outside/evil.pdf",
            file_type="pdf",
            file_data=b"%PDF-1.7 test",
        )

    meta = asyncio.run(flow())
    saved = Path(meta["saved_file_path"])
    # Stored under the server-controlled name, inside the session directory.
    assert saved.name == "original.pdf"
    assert meta["session_id"] in saved.parts
    assert meta["upload_id"] in saved.parts
    assert "outside" not in saved.parts
    # The original name survives only as sanitized display metadata.
    assert meta["file_name"] == "evil.pdf"


def test_get_upload_cache_miss_falls_back_to_disk(repo):
    async def flow():
        session_id = await repo.create_session()
        meta = await repo.create_upload(
            session_id=session_id,
            display_name="a.pdf",
            file_type="pdf",
            file_data=b"%PDF-1.7 x",
        )
        # A fresh repository has a cold cache but shares the disk store.
        cold = SessionRepository()
        return meta, await cold.get_upload(session_id, meta["upload_id"])

    meta, fetched = asyncio.run(flow())
    assert fetched is not None
    assert fetched["upload_id"] == meta["upload_id"]


def test_get_upload_missing_returns_none(repo):
    result = asyncio.run(repo.get_upload("no-such-session", "no-such-upload"))
    assert result is None


def test_update_stage_roundtrip(repo):
    from app.models.resume_processing_stages import ResumeProcessingStages

    async def flow():
        session_id = await repo.create_session()
        meta = await repo.create_upload(
            session_id=session_id,
            display_name="a.pdf",
            file_type="pdf",
            file_data=b"%PDF-1.7 x",
        )
        updated = await repo.update_stage(
            session_id, meta["upload_id"], ResumeProcessingStages.PARSED
        )
        fetched = await repo.get_upload(session_id, meta["upload_id"])
        return updated, fetched

    updated, fetched = asyncio.run(flow())
    assert updated["status"] == "parsed"
    assert fetched["status"] == "parsed"
