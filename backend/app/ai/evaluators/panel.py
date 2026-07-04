"""Persona evaluation panel: recruiter, ATS auditor, and hiring manager each
judge the resume independently; the panel aggregates their verdicts."""

import asyncio
import json

from pydantic import BaseModel, Field, ValidationError

from app.ai.evaluators import load_prompt, parse_json_response
from app.ai.llm.client import complete_with_retry
from app.ai.llm.provider import LLMProvider, PromptPayload, build_data_prompt
from app.core.exceptions import EvaluationFailedError
from app.core.logging import AppLogger
from app.models.resume_document import ResumeDocument

logger = AppLogger("PanelEvaluator")

PERSONAS = {
    "recruiter": "persona_recruiter.txt",
    "ats": "persona_ats.txt",
    "hiring_manager": "persona_hiring_manager.txt",
}


class PersonaResult(BaseModel):
    persona: str
    score: int = Field(ge=0, le=100)
    verdict: str
    highlights: list[str] = []
    concerns: list[str] = []


class PanelResult(BaseModel):
    overall_score: int
    verdicts: list[PersonaResult]
    model: str
    prompt_version: str


class PanelEvaluator:
    def __init__(self, provider: LLMProvider):
        self.provider = provider

    async def evaluate(self, resume: ResumeDocument) -> PanelResult:
        resume_json = json.dumps(resume.model_dump(mode="json"), indent=2)
        results = await asyncio.gather(
            *(
                self._run_persona(name, prompt_file, resume_json)
                for name, prompt_file in PERSONAS.items()
            )
        )
        verdicts = [r for r, _, _ in results]
        _, model, version = results[0]
        overall = round(sum(v.score for v in verdicts) / len(verdicts))
        logger.info(f"Panel complete: overall={overall} (model={model})")
        return PanelResult(
            overall_score=overall,
            verdicts=verdicts,
            model=model,
            prompt_version=version,
        )

    async def _run_persona(
        self, name: str, prompt_file: str, resume_json: str
    ) -> tuple[PersonaResult, str, str]:
        version, system = load_prompt(prompt_file)
        payload = PromptPayload(
            system=system,
            user_content=build_data_prompt(
                f"Evaluate the following resume data as the {name} persona.",
                resume_json,
            ),
        )
        result = await complete_with_retry(self.provider, payload)
        data = parse_json_response(f"panel:{name}", result.text)
        try:
            verdict = PersonaResult(persona=name, **data)
        except ValidationError as e:
            raise EvaluationFailedError(
                step=f"panel:{name}", reason=f"schema mismatch: {e}"
            ) from e
        return verdict, result.model, version
