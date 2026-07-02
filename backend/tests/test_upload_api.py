"""API-level tests for /resume/upload: validation and the end-to-end pipeline."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_upload_rejects_spoofed_content_type(client):
    # Declared as PDF, but the bytes are not a supported format.
    response = client.post(
        "/resume/upload",
        files={"file": ("evil.pdf", b"<html>not a pdf</html>", "application/pdf")},
    )
    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]


def test_upload_rejects_oversized_file(client):
    big = b"%PDF-" + b"0" * (settings.upload_max_size + 1)
    response = client.post(
        "/resume/upload",
        files={"file": ("big.pdf", big, "application/pdf")},
    )
    assert response.status_code == 413


def test_upload_traversal_filename_is_neutralised(client):
    pdf_bytes = (FIXTURES / "sample_resume.pdf").read_bytes()
    response = client.post(
        "/resume/upload",
        files={"file": ("../../evil.pdf", pdf_bytes, "application/pdf")},
    )
    assert response.status_code == 200
    body = response.json()
    # Nothing was written outside the storage root.
    storage_root = Path(settings.storage_path).resolve()
    session_dir = storage_root / body["session_id"] / body["upload_id"]
    assert (session_dir / "original.pdf").exists()
    assert not (storage_root.parent / "evil.pdf").exists()


def test_upload_pdf_end_to_end(client):
    pdf_bytes = (FIXTURES / "sample_resume.pdf").read_bytes()
    response = client.post(
        "/resume/upload",
        files={"file": ("resume.pdf", pdf_bytes, "application/pdf")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "parsed"

    session_dir = (
        Path(settings.storage_path).resolve() / body["session_id"] / body["upload_id"]
    )
    for artefact in ("metadata.json", "document_tree.json", "resume_extracted.json"):
        assert (session_dir / artefact).exists(), f"missing {artefact}"


def test_upload_docx_end_to_end(client):
    docx_bytes = (FIXTURES / "sample_resume.docx").read_bytes()
    response = client.post(
        "/resume/upload",
        files={
            "file": (
                "resume.docx",
                docx_bytes,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "parsed"
