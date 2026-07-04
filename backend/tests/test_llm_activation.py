"""Tests for runtime LLM provider activation (GET /llm/providers, POST /llm/activate)."""

import json

import pytest
from fastapi.testclient import TestClient

from app.ai.llm import registry
from app.ai.llm.client import get_llm_provider
from app.ai.llm.adapters import AnthropicAdapter
from app.ai.llm.provider import FakeLLMProvider
from app.core.config import settings
from app.main import app


@pytest.fixture()
def client():
    return TestClient(app)


def test_list_providers_reports_status(client):
    response = client.get("/llm/providers")
    assert response.status_code == 200
    body = response.json()
    by_name = {p["name"]: p for p in body["providers"]}
    assert set(by_name) == {"anthropic", "openai", "google", "bedrock", "fake"}
    # fake needs neither key nor package
    assert by_name["fake"]["api_key_configured"] is True
    assert by_name["fake"]["package_installed"] is True
    # CI has no provider packages installed -> install hints exposed
    assert by_name["anthropic"]["install_hint"] in (None, "pip install langchain-anthropic")
    assert by_name["bedrock"]["api_key_configured"] is True  # AWS chain, no key


def test_activate_fake_provider_switches_runtime(client):
    response = client.post("/llm/activate", json={"provider": "fake"})
    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "fake"
    assert isinstance(get_llm_provider(), FakeLLMProvider)
    # GET reflects the activation
    providers = client.get("/llm/providers").json()
    assert providers["active_provider"] == "fake"


def test_activate_unknown_provider_rejected(client):
    response = client.post("/llm/activate", json={"provider": "skynet"})
    assert response.status_code == 400
    assert "unknown provider" in response.json()["message"]


def test_activate_without_api_key_rejected(client, monkeypatch):
    # Ensure no key is configured for anthropic in any form.
    monkeypatch.setattr(settings, "anthropic_api_key", "")
    monkeypatch.setattr(settings, "llm_api_key", "")
    # Pretend the package is installed so the key check is what trips.
    monkeypatch.setattr(registry, "package_installed", lambda info: True)
    response = client.post("/llm/activate", json={"provider": "anthropic"})
    assert response.status_code == 400
    assert "ANTHROPIC_API_KEY" in response.json()["message"]


def test_activate_missing_package_rejected(client, monkeypatch):
    monkeypatch.setattr(settings, "anthropic_api_key", "sk-test")
    monkeypatch.setattr(registry, "package_installed", lambda info: False)
    response = client.post("/llm/activate", json={"provider": "anthropic"})
    assert response.status_code == 400
    assert "pip install langchain-anthropic" in response.json()["message"]


def test_activate_with_key_and_package_selects_adapter(client, monkeypatch):
    monkeypatch.setattr(settings, "anthropic_api_key", "sk-test")
    monkeypatch.setattr(settings, "llm_api_key", "")
    monkeypatch.setattr(registry, "package_installed", lambda info: True)
    response = client.post(
        "/llm/activate", json={"provider": "anthropic", "model": "claude-sonnet-5"}
    )
    assert response.status_code == 200
    assert response.json()["model"] == "claude-sonnet-5"
    provider = get_llm_provider()
    assert isinstance(provider, AnthropicAdapter)
    assert provider.model == "claude-sonnet-5"
    assert provider.api_key == "sk-test"


def test_alias_names_accepted(client, monkeypatch):
    monkeypatch.setattr(registry, "package_installed", lambda info: True)
    response = client.post("/llm/activate", json={"provider": "aws"})
    assert response.status_code == 200
    assert response.json()["provider"] == "bedrock"


def test_activation_drives_evaluation_endpoint(client, monkeypatch):
    """End to end: upload -> activate fake -> evaluate uses the activated provider."""
    from pathlib import Path

    monkeypatch.setattr(
        settings,
        "llm_fake_response",
        json.dumps(
            {
                "strengths": ["s"], "weaknesses": ["w"], "ats_score": 70,
                "readability_score": 80, "missing_skills": [], "suggestions": [],
            }
        ),
    )
    fixtures = Path(__file__).parent / "fixtures"
    upload = client.post(
        "/resume/upload",
        files={"file": ("r.pdf", (fixtures / "sample_resume.pdf").read_bytes(), "application/pdf")},
    ).json()

    # Without activation (and no env provider) evaluation is 503.
    monkeypatch.setattr(settings, "llm_provider", "")
    response = client.post(f"/resume/{upload['session_id']}/{upload['upload_id']}/evaluate")
    assert response.status_code == 503

    # Activate at runtime via the API - no restart - and evaluate again.
    assert client.post("/llm/activate", json={"provider": "fake"}).status_code == 200
    response = client.post(f"/resume/{upload['session_id']}/{upload['upload_id']}/evaluate")
    assert response.status_code == 200
    assert response.json()["ats_score"] == 70
