"""Peer benchmarking: embed a candidate profile, index it, find similar peers.

The profile text is built from the structured ResumeDocument (skills + roles),
so what gets embedded is the career signature - not raw resume prose.
"""

from app.ai.llm.embeddings import EmbeddingsProvider
from app.core.logging import AppLogger
from app.models.resume_document import ResumeDocument
from app.storage.vector_index import VectorIndexProtocol

logger = AppLogger("BenchmarkService")


def build_profile_text(resume: ResumeDocument) -> str:
    """Deterministic career-signature text used for embedding."""
    skills = " ".join(s.name for s in resume.skills)
    roles = " ".join(f"{e.title} {e.company}" for e in resume.work_ex)
    return f"skills: {skills}\nroles: {roles}".strip()


class BenchmarkService:
    def __init__(self, index: VectorIndexProtocol, embeddings: EmbeddingsProvider):
        self.index = index
        self.embeddings = embeddings

    async def index_resume(
        self, session_id: str, upload_id: str, resume: ResumeDocument
    ) -> dict:
        profile = build_profile_text(resume)
        [vector] = await self.embeddings.embed([profile])
        entry = {
            "candidate_id": f"{session_id}/{upload_id}",
            "vector": vector,
            "skills": sorted({s.name.lower() for s in resume.skills}),
            "titles": [e.title for e in resume.work_ex],
        }
        await self.index.add(entry)
        return entry

    async def find_peers(
        self, session_id: str, upload_id: str, resume: ResumeDocument, top_k: int
    ) -> list[dict]:
        """Top-k most similar indexed candidates, with skill-gap analysis."""
        profile = build_profile_text(resume)
        [vector] = await self.embeddings.embed([profile])
        own_skills = {s.name.lower() for s in resume.skills}

        peers = await self.index.query(
            vector, top_k=top_k, exclude_id=f"{session_id}/{upload_id}"
        )
        results = []
        for peer in peers:
            peer_skills = set(peer.get("skills", []))
            results.append(
                {
                    "candidate_id": peer["candidate_id"],
                    "similarity": peer["similarity"],
                    "titles": peer.get("titles", []),
                    "shared_skills": sorted(own_skills & peer_skills),
                    # Skills common among peers but missing here = growth signal.
                    "skills_you_lack": sorted(peer_skills - own_skills),
                }
            )
        return results
