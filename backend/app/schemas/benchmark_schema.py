"""API schemas for peer benchmarking and the persona evaluation panel."""

from pydantic import BaseModel, Field


class IndexedResponse(BaseModel):
    message: str
    candidate_id: str
    skills_indexed: int
    index_size: int


class PeerMatch(BaseModel):
    candidate_id: str
    similarity: float
    titles: list[str]
    shared_skills: list[str]
    skills_you_lack: list[str]


class SimilarResponse(BaseModel):
    session_id: str
    upload_id: str
    peers: list[PeerMatch]


class PersonaVerdict(BaseModel):
    persona: str
    score: int = Field(ge=0, le=100)
    verdict: str
    highlights: list[str]
    concerns: list[str]


class PanelResponse(BaseModel):
    session_id: str
    upload_id: str
    overall_score: int
    verdicts: list[PersonaVerdict]
    model: str
    prompt_version: str
