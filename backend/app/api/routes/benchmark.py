"""Peer benchmarking endpoints: index a parsed resume, find similar candidates."""

from uuid import UUID

from fastapi import APIRouter, Query

from app.api.deps import session_repository
from app.ai.llm.embeddings import get_embeddings_provider
from app.core.exceptions import NotFoundError
from app.core.logging import AppLogger
from app.models.resume_document import ResumeDocument
from app.schemas.benchmark_schema import IndexedResponse, SimilarResponse, PeerMatch
from app.services.benchmark_service import BenchmarkService
from app.storage.vector_index import FileVectorIndex

router = APIRouter(prefix="/resume", tags=["Peer benchmarking"])

logger = AppLogger("BenchmarkRoute")

vector_index = FileVectorIndex()


async def _load_resume(session_id: UUID, upload_id: UUID) -> ResumeDocument:
    data = await session_repository.get_extraction(str(session_id), str(upload_id))
    if data is None:
        raise NotFoundError(resource_type="Extraction", resource_id=str(upload_id))
    return ResumeDocument(**data)


@router.post(
    "/{session_id}/{upload_id}/index",
    response_model=IndexedResponse,
    summary="Add a parsed resume to the peer-benchmarking index",
)
async def index_resume(session_id: UUID, upload_id: UUID):
    resume = await _load_resume(session_id, upload_id)
    service = BenchmarkService(vector_index, get_embeddings_provider())
    entry = await service.index_resume(str(session_id), str(upload_id), resume)
    return IndexedResponse(
        message="Candidate indexed for benchmarking",
        candidate_id=entry["candidate_id"],
        skills_indexed=len(entry["skills"]),
        index_size=await vector_index.count(),
    )


@router.get(
    "/{session_id}/{upload_id}/similar",
    response_model=SimilarResponse,
    summary="Find indexed candidates most similar to this resume",
)
async def similar_candidates(
    session_id: UUID,
    upload_id: UUID,
    top_k: int = Query(default=5, ge=1, le=50),
):
    resume = await _load_resume(session_id, upload_id)
    service = BenchmarkService(vector_index, get_embeddings_provider())
    peers = await service.find_peers(str(session_id), str(upload_id), resume, top_k)
    return SimilarResponse(
        session_id=str(session_id),
        upload_id=str(upload_id),
        peers=[PeerMatch(**p) for p in peers],
    )
