"""Process-wide service singletons shared by all routes.

One SessionRepository (and its cache) for the whole app; the parsing service
reuses it so stage updates and reads stay consistent across endpoints.
"""

from app.storage.session_repository import SessionRepository
from app.services.resume_parsing_service import ResumeParsingService

session_repository = SessionRepository()
resume_parsing_service = ResumeParsingService(session_repository=session_repository)
