"""LLM-backed job-description matching."""

import json

from pydantic import ValidationError

from app.ai.evaluators import load_prompt, parse_json_response
from app.ai.llm.client import complete_with_retry
from app.ai.llm.provider import LLMProvider, PromptPayload, build_data_prompt
from app.core.exceptions import EvaluationFailedError
from app.core.logging import AppLogger
from app.models.jd import JDMatchResult
from app.models.resume_document import ResumeDocument

logger = AppLogger("JDMatcher")


class JDMatcher:
    def __init__(self, provider: LLMProvider):
        self.provider = provider

    async def match(self, resume: ResumeDocument, jd_text: str) -> JDMatchResult:
        version, system = load_prompt("jd_match.txt")
        combined = json.dumps(
            {
                "job_description": jd_text,
                "resume": resume.model_dump(mode="json"),
            },
            indent=2,
        )
        payload = PromptPayload(
            system=system,
            user_content=build_data_prompt(
                "Match the resume against the job description below.", combined
            ),
        )
        result = await complete_with_retry(self.provider, payload)
        data = parse_json_response("jd_match", result.text)
        try:
            match = JDMatchResult(
                **data,
                prompt_version=version,
                model=result.model,
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
            )
        except ValidationError as e:
            raise EvaluationFailedError(
                step="jd_match", reason=f"schema mismatch: {e}"
            ) from e
        logger.info(f"JD matched (model={result.model})")
        return match
