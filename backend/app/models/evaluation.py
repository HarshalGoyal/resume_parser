from pydantic import BaseModel


class Evaluation(BaseModel):
    """AI evaluation of a parsed resume."""

    strengths: list[str] = []
    weaknesses: list[str] = []
    ats_score: int  # 0-100
    readability_score: int  # 0-100
    missing_skills: list[str] = []
    suggestions: list[str] = []
    # Provenance / reproducibility
    prompt_version: str = ""
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
