"""Phase 5 tests: embeddings, vector index, peer benchmarking, persona panel."""

import asyncio
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.ai.llm.embeddings import FakeEmbeddings, get_embeddings_provider
from app.core.config import settings
from app.core.exceptions import LLMNotConfiguredError
from app.main import app
from app.storage.vector_index import FileVectorIndex, cosine_similarity

FIXTURES = Path(__file__).parent / "fixtures"

PERSONA_JSON = json.dumps(
    {
        "score": 80,
        "verdict": "Solid senior-engineer profile.",
        "highlights": ["distributed systems"],
        "concerns": ["no public portfolio"],
    }
)


# --- Embeddings ---------------------------------------------------------------

def test_fake_embeddings_deterministic_and_similarity_ordering():
    emb = FakeEmbeddings()
    [a1] = asyncio.run(emb.embed(["python fastapi docker"]))
    [a2] = asyncio.run(emb.embed(["python fastapi docker"]))
    [close] = asyncio.run(emb.embed(["python fastapi kubernetes"]))
    [far] = asyncio.run(emb.embed(["watercolor painting pottery"]))
    assert a1 == a2  # deterministic
    assert cosine_similarity(a1, close) > cosine_similarity(a1, far)


def test_embeddings_factory(monkeypatch):
    monkeypatch.setattr(settings, "embeddings_provider", "fake")
    assert isinstance(get_embeddings_provider(), FakeEmbeddings)

    monkeypatch.setattr(settings, "embeddings_provider", "")
    with pytest.raises(LLMNotConfiguredError):
        get_embeddings_provider()

    # openai package not installed in CI -> actionable hint
    monkeypatch.setattr(settings, "embeddings_provider", "openai")
    with pytest.raises(LLMNotConfiguredError) as exc_info:
        get_embeddings_provider()
    assert "pip install langchain-openai" in str(exc_info.value)


# --- Vector index ---------------------------------------------------------------

def test_vector_index_add_query_replace(tmp_path):
    index = FileVectorIndex(tmp_path / "index.json")

    async def flow():
        await index.add({"candidate_id": "a", "vector": [1.0, 0.0], "skills": ["x"]})
        await index.add({"candidate_id": "b", "vector": [0.9, 0.1], "skills": ["y"]})
        await index.add({"candidate_id": "c", "vector": [0.0, 1.0], "skills": ["z"]})
        # Re-indexing replaces, not duplicates.
        await index.add({"candidate_id": "a", "vector": [1.0, 0.0], "skills": ["x2"]})
        top = await index.query([1.0, 0.0], top_k=2, exclude_id="a")
        return await index.count(), top

    count, top = asyncio.run(flow())
    assert count == 3
    assert [t["candidate_id"] for t in top] == ["b", "c"]
    assert top[0]["similarity"] > top[1]["similarity"]


# --- Benchmarking API -----------------------------------------------------------

@pytest.fixture()
def client():
    return TestClient(app)


def _upload(client, name="r.pdf"):
    return client.post(
        "/resume/upload",
        files={"file": (name, (FIXTURES / "sample_resume.pdf").read_bytes(), "application/pdf")},
    ).json()


def test_benchmark_index_and_similar_end_to_end(client, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "embeddings_provider", "fake")
    # Isolate this test's index file.
    from app.api.routes import benchmark

    monkeypatch.setattr(benchmark, "vector_index", FileVectorIndex(tmp_path / "ix.json"))

    first = _upload(client)
    second = _upload(client)

    for up in (first, second):
        response = client.post(f"/resume/{up['session_id']}/{up['upload_id']}/index")
        assert response.status_code == 200

    assert response.json()["index_size"] == 2

    similar = client.get(
        f"/resume/{first['session_id']}/{first['upload_id']}/similar?top_k=3"
    )
    assert similar.status_code == 200
    peers = similar.json()["peers"]
    # Self is excluded; the other (identical) resume matches ~perfectly.
    assert len(peers) == 1
    assert peers[0]["candidate_id"] == f"{second['session_id']}/{second['upload_id']}"
    assert peers[0]["similarity"] > 0.99
    assert peers[0]["skills_you_lack"] == []  # identical skill sets


def test_benchmark_requires_embeddings_provider(client, monkeypatch):
    monkeypatch.setattr(settings, "embeddings_provider", "")
    up = _upload(client)
    response = client.post(f"/resume/{up['session_id']}/{up['upload_id']}/index")
    assert response.status_code == 503


def test_benchmark_unknown_upload_404(client, monkeypatch):
    from uuid import uuid4

    monkeypatch.setattr(settings, "embeddings_provider", "fake")
    assert client.post(f"/resume/{uuid4()}/{uuid4()}/index").status_code == 404
    assert client.get(f"/resume/{uuid4()}/{uuid4()}/similar").status_code == 404


# --- Persona panel ---------------------------------------------------------------

def test_panel_end_to_end_with_fake_provider(client, monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "fake")
    monkeypatch.setattr(settings, "llm_fake_response", PERSONA_JSON)

    up = _upload(client)
    response = client.post(f"/resume/{up['session_id']}/{up['upload_id']}/panel")
    assert response.status_code == 200
    body = response.json()
    assert body["overall_score"] == 80
    assert {v["persona"] for v in body["verdicts"]} == {
        "recruiter", "ats", "hiring_manager",
    }
    for verdict in body["verdicts"]:
        assert verdict["score"] == 80
        assert verdict["verdict"]
    assert body["prompt_version"] == "1"


def test_panel_503_without_provider(client, monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "")
    up = _upload(client)
    response = client.post(f"/resume/{up['session_id']}/{up['upload_id']}/panel")
    assert response.status_code == 503


def test_panel_rejects_malformed_persona_output(client, monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "fake")
    monkeypatch.setattr(settings, "llm_fake_response", '{"score": 200}')  # invalid
    up = _upload(client)
    response = client.post(f"/resume/{up['session_id']}/{up['upload_id']}/panel")
    assert response.status_code == 502
