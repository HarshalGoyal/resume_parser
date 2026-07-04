"""Tests for the Phase 2 results endpoints and upload response contract."""

from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture(scope="module")
def uploaded(client):
    """Upload the sample PDF once; returns the upload response body."""
    pdf_bytes = (FIXTURES / "sample_resume.pdf").read_bytes()
    response = client.post(
        "/resume/upload",
        files={"file": ("resume.pdf", pdf_bytes, "application/pdf")},
    )
    assert response.status_code == 200
    return response.json()


def test_upload_returns_links(uploaded):
    base = f"/resume/{uploaded['session_id']}/{uploaded['upload_id']}"
    assert uploaded["links"] == {"result": base, "status": f"{base}/status"}


def test_get_extraction_happy_path(client, uploaded):
    response = client.get(uploaded["links"]["result"])
    assert response.status_code == 200
    body = response.json()
    assert body["session_id"] == uploaded["session_id"]
    assert body["upload_id"] == uploaded["upload_id"]
    skill_names = {s["name"].lower() for s in body["skills"]}
    assert "python" in skill_names
    assert len(body["work_experience"]) == 3
    for job in body["work_experience"]:
        assert set(job) == {"title", "company", "duration", "description"}


def test_get_status_happy_path(client, uploaded):
    response = client.get(uploaded["links"]["status"])
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "parsed"
    assert body["file_type"] == "pdf"
    assert body["error_message"] is None


def test_get_extraction_unknown_ids_404(client):
    response = client.get(f"/resume/{uuid4()}/{uuid4()}")
    assert response.status_code == 404
    body = response.json()
    assert body["error_code"] == "API_002"


def test_get_status_unknown_ids_404(client):
    response = client.get(f"/resume/{uuid4()}/{uuid4()}/status")
    assert response.status_code == 404


def test_non_uuid_path_params_rejected(client):
    response = client.get("/resume/not-a-uuid/also-not-a-uuid")
    assert response.status_code == 422
