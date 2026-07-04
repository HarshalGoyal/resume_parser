"""API response schemas (DTOs) for resume extraction results.

These own the wire format. Domain models (app.models.*) stay internal; every
route maps domain -> DTO explicitly so internal refactors never silently change
the API contract.
"""

from pydantic import BaseModel

from app.models.resume_document import ResumeDocument


class ContactInfoResponse(BaseModel):
    emails: list[str] = []
    phone_numbers: list[str] = []
    linkedin_profiles: list[str] = []
    github_profiles: list[str] = []
    other_links: list[str] = []


class SkillResponse(BaseModel):
    name: str
    confidence_score: float = 1.0


class ExperienceResponse(BaseModel):
    title: str
    company: str
    duration: str
    description: str


class ResumeExtractionResponse(BaseModel):
    session_id: str
    upload_id: str
    contact_info: ContactInfoResponse
    skills: list[SkillResponse]
    work_experience: list[ExperienceResponse]


def to_extraction_response(
    session_id: str, upload_id: str, resume: ResumeDocument
) -> ResumeExtractionResponse:
    """Map the ResumeDocument domain model to its API representation."""
    return ResumeExtractionResponse(
        session_id=session_id,
        upload_id=upload_id,
        contact_info=ContactInfoResponse(**resume.contact_info.model_dump()),
        skills=[SkillResponse(**s.model_dump()) for s in resume.skills],
        work_experience=[ExperienceResponse(**e.model_dump()) for e in resume.work_ex],
    )
