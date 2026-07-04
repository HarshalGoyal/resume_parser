"""Phase 4 tests: auth, observability, TTL cleanup, background parsing,
and the SQL metadata repository."""

import asyncio
import os
import time
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.models.resume_processing_stages import ResumeProcessingStages
from app.services.cleanup_service import cleanup_expired_sessions
from app.storage.session_repository import SessionRepository
from app.storage.sql_session_repository import SQLSessionRepository, UploadRow

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture()
def client():
    return TestClient(app)


# --- API-key auth -----------------------------------------------------------

def test_auth_disabled_by_default(client):
    assert client.get("/info").status_code == 200


def test_auth_enforced_when_key_set(client, monkeypatch):
    monkeypatch.setattr(settings, "api_key", "secret-key")
    assert client.get("/info").status_code == 401
    assert client.get("/info", headers={"X-API-Key": "wrong"}).status_code == 401
    assert client.get("/info", headers={"X-API-Key": "secret-key"}).status_code == 200
    body = client.get("/info").json()
    assert body["error_code"] == "AUTH_001"


def test_auth_exempts_health_and_root(client, monkeypatch):
    monkeypatch.setattr(settings, "api_key", "secret-key")
    assert client.get("/health/").status_code == 200
    assert client.get("/").status_code == 200
    assert client.get("/docs").status_code == 200


def test_auth_protects_llm_activation(client, monkeypatch):
    monkeypatch.setattr(settings, "api_key", "secret-key")
    response = client.post("/llm/activate", json={"provider": "fake"})
    assert response.status_code == 401


# --- Observability ----------------------------------------------------------

def test_request_id_header_attached(client):
    response = client.get("/health/")
    assert response.headers.get("X-Request-ID")


def test_incoming_request_id_is_echoed(client):
    response = client.get("/health/", headers={"X-Request-ID": "trace-me-123"})
    assert response.headers["X-Request-ID"] == "trace-me-123"


def test_metrics_endpoint_exposes_counters(client):
    client.get("/health/")  # ensure at least one request is recorded
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "http_requests_total" in response.text
    assert "http_request_duration_seconds" in response.text


# --- TTL cleanup ------------------------------------------------------------

def test_cleanup_removes_only_expired_sessions(monkeypatch):
    storage_root = Path(settings.storage_path).resolve()
    old_dir = storage_root / "expired-session"
    fresh_dir = storage_root / "fresh-session"
    (old_dir / "upload1").mkdir(parents=True, exist_ok=True)
    (fresh_dir / "upload1").mkdir(parents=True, exist_ok=True)
    (old_dir / "upload1" / "metadata.json").write_text("{}")
    (fresh_dir / "upload1" / "metadata.json").write_text("{}")

    # Age every file/dir in the expired session beyond the TTL.
    monkeypatch.setattr(settings, "session_timeout_minutes", 10)
    stale = time.time() - 3600
    for p in [old_dir, *old_dir.rglob("*")]:
        os.utime(p, (stale, stale))

    removed = asyncio.run(cleanup_expired_sessions(SessionRepository()))
    assert removed >= 1
    assert not old_dir.exists()
    assert fresh_dir.exists()


# --- Background parsing -----------------------------------------------------

def test_background_parse_failure_is_recorded(client):
    # Valid PDF magic bytes but corrupt content: upload succeeds (queued),
    # parsing fails in the background, and the status endpoint reports it.
    response = client.post(
        "/resume/upload",
        files={"file": ("bad.pdf", b"%PDF-1.7 not really a pdf", "application/pdf")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "queued"

    status = client.get(body["links"]["status"]).json()
    assert status["status"] == "failed"
    assert status["error_message"]


# --- SQL metadata repository -------------------------------------------------

@pytest.fixture()
def sql_repo(tmp_path):
    return SQLSessionRepository(f"sqlite+aiosqlite:///{tmp_path}/sessions.db")


def test_sql_repo_roundtrip(sql_repo):
    async def flow():
        session_id = await sql_repo.create_session()
        meta = await sql_repo.create_upload(
            session_id=session_id,
            display_name="r.pdf",
            file_type="pdf",
            file_data=b"%PDF-1.7 test",
        )
        fetched = await sql_repo.get_upload(session_id, meta["upload_id"])
        staged = await sql_repo.update_stage(
            session_id, meta["upload_id"], ResumeProcessingStages.PARSED
        )
        failed = await sql_repo.mark_failed(session_id, meta["upload_id"], "boom")
        return meta, fetched, staged, failed

    meta, fetched, staged, failed = asyncio.run(flow())
    assert fetched["upload_id"] == meta["upload_id"]
    assert Path(meta["saved_file_path"]).exists()
    assert staged["status"] == "parsed"
    assert failed["status"] == "failed"
    assert failed["error_message"] == "boom"
    assert failed["retry_count"] == 1


def test_sql_repo_missing_upload_returns_none(sql_repo):
    assert asyncio.run(sql_repo.get_upload("nope", "nope")) is None
    assert asyncio.run(sql_repo.get_extraction("nope", "nope")) is None


def test_sql_repo_purge_expired(sql_repo):
    async def flow():
        session_id = await sql_repo.create_session()
        meta = await sql_repo.create_upload(
            session_id=session_id,
            display_name="r.pdf",
            file_type="pdf",
            file_data=b"%PDF-1.7 test",
        )
        # Backdate the row well past any TTL.
        async with sql_repo.session_factory() as db:
            row = await db.get(UploadRow, (session_id, meta["upload_id"]))
            row.updated_at = datetime.now() - timedelta(days=30)
            await db.commit()
        purged = await sql_repo.purge_expired(ttl_seconds=60)
        remaining = await sql_repo.list_all()
        return purged, remaining

    purged, remaining = asyncio.run(flow())
    assert purged == 1
    assert remaining == []


def test_deps_selects_sql_repo_when_database_url_set(monkeypatch, tmp_path):
    from app.api.deps import build_session_repository

    monkeypatch.setattr(settings, "database_url", f"sqlite+aiosqlite:///{tmp_path}/x.db")
    assert isinstance(build_session_repository(), SQLSessionRepository)
    monkeypatch.setattr(settings, "database_url", "")
    assert isinstance(build_session_repository(), SessionRepository)
