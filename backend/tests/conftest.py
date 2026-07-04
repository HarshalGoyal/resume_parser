"""Shared test configuration.

Points the app's storage at a throwaway directory BEFORE any app module is
imported (settings and FileStore resolve the storage path at import time), so
tests never write into the real working storage area.
"""

import os
import tempfile

import pytest

_TEST_STORAGE = tempfile.mkdtemp(prefix="resume_parser_test_storage_")
os.environ.setdefault("STORAGE_PATH", _TEST_STORAGE)
os.environ.setdefault("LOG_FILE", os.path.join(_TEST_STORAGE, "test.log"))


@pytest.fixture(autouse=True)
def _reset_llm_activation():
    """Runtime provider activation is process-wide state; isolate tests."""
    from app.ai.llm import registry

    registry.reset_active()
    yield
    registry.reset_active()
