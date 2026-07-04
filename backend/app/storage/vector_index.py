"""Candidate vector index for peer benchmarking.

VectorIndexProtocol is the seam: the file-backed implementation below is right
for the current scale (pure-python cosine over a JSON file); pgvector/Qdrant
implementations can replace it without touching the benchmark service.
"""

import asyncio
import json
import math
from pathlib import Path
from typing import Protocol

from app.core.config import settings
from app.core.logging import AppLogger

logger = AppLogger("VectorIndex")


class VectorIndexProtocol(Protocol):
    async def add(self, entry: dict) -> None: ...

    async def query(
        self, vector: list[float], top_k: int, exclude_id: str = ""
    ) -> list[dict]: ...

    async def count(self) -> int: ...


def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class FileVectorIndex:
    """JSON-file-backed index. Entries: {candidate_id, vector, skills, titles}."""

    def __init__(self, path: str | Path | None = None):
        self.path = Path(
            path or Path(settings.storage_path).resolve() / "vector_index.json"
        )

    def _load(self) -> list[dict]:
        if not self.path.exists():
            return []
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _save(self, entries: list[dict]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(entries), encoding="utf-8")

    async def add(self, entry: dict) -> None:
        def _add():
            entries = self._load()
            # Re-indexing the same candidate replaces its entry.
            entries = [
                e for e in entries if e["candidate_id"] != entry["candidate_id"]
            ]
            entries.append(entry)
            self._save(entries)

        await asyncio.to_thread(_add)
        logger.info(f"Indexed candidate {entry['candidate_id']}")

    async def query(
        self, vector: list[float], top_k: int, exclude_id: str = ""
    ) -> list[dict]:
        entries = await asyncio.to_thread(self._load)
        scored = [
            {**e, "similarity": round(cosine_similarity(vector, e["vector"]), 4)}
            for e in entries
            if e["candidate_id"] != exclude_id
        ]
        scored.sort(key=lambda e: e["similarity"], reverse=True)
        return scored[:top_k]

    async def count(self) -> int:
        return len(await asyncio.to_thread(self._load))
