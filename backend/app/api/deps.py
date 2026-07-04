"""Process-wide service singletons shared by all routes.

One repository (and its cache) for the whole app; the parsing service reuses
it so stage updates and reads stay consistent across endpoints. The metadata
repository is file-backed by default and SQL-backed when DATABASE_URL is set.
"""

from app.core.config import settings
from app.storage.base import SessionRepositoryProtocol
from app.storage.session_repository import SessionRepository
from app.services.resume_parsing_service import ResumeParsingService


def build_session_repository() -> SessionRepositoryProtocol:
    if settings.database_url:
        from app.storage.sql_session_repository import SQLSessionRepository

        return SQLSessionRepository(settings.database_url)
    return SessionRepository()


session_repository: SessionRepositoryProtocol = build_session_repository()
resume_parsing_service = ResumeParsingService(session_repository=session_repository)
