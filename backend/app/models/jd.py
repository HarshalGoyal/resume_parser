from pydantic import BaseModel


class JDMatchResult(BaseModel):
    """Result of matching a resume against a job description."""

    match_percentage: int  # 0-100
    missing_skills: list[str] = []
    role_alignment: str = ""
    suggestions: list[str] = []
    # Provenance / reproducibility
    prompt_version: str = ""
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
