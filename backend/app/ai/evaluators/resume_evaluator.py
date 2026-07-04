"""LLM-backed resume evaluation."""

import json

from pydantic import ValidationError

from app.ai.evaluators import load_prompt, parse_json_response
from app.ai.llm.client import complete_with_retry
from app.ai.llm.provider import LLMProvider, PromptPayload, build_data_prompt
from app.core.exceptions import EvaluationFailedError
from app.core.logging import AppLogger
from app.models.evaluation import Evaluation
from app.models.resume_document import ResumeDocument

logger = AppLogger("ResumeEvaluator")


class ResumeEvaluator:
    def __init__(self, provider: LLMProvider):
        self.provider = provider

    async def evaluate(self, resume: ResumeDocument) -> Evaluation:
        version, system = load_prompt("resume_feedback.txt")
        resume_json = json.dumps(resume.model_dump(mode="json"), indent=2)
        payload = PromptPayload(
            system=system,
            user_content=build_data_prompt(
                "Evaluate the following resume data.", resume_json
            ),
        )
        result = await complete_with_retry(self.provider, payload)
        data = parse_json_response("resume_evaluation", result.text)
        try:
            evaluation = Evaluation(
                **data,
                prompt_version=version,
                model=result.model,
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
            )
        except ValidationError as e:
            raise EvaluationFailedError(
                step="resume_evaluation", reason=f"schema mismatch: {e}"
            ) from e
        logger.info(
            f"Resume evaluated (model={result.model}, "
            f"tokens={result.input_tokens}+{result.output_tokens})"
        )
        return evaluation
