"""Integration test: parse the synthetic sample resume end to end.

The fixture (backend/tests/fixtures/sample_resume.docx) uses fake data but
reproduces the structural challenges from the 2026-07-02 DOCX test — combined
"Title  Company  Dates" header lines (multi-space and tab separated),
"Category: list" skills with a parenthetical, bold bullets, and a bold
mixed-case project title. It guards against those regressions while the
underlying logic stays generic.
"""

import asyncio
import re
from pathlib import Path

import pytest

from app.ai.parsers.docx_parser import DOCXParser
from app.services.resume_enrichment_service import ResumeEnrichmentService

FIXTURE = Path(__file__).parent / "fixtures" / "sample_resume.docx"


@pytest.fixture(scope="module")
def parsed():
    doc = asyncio.run(DOCXParser().parse(str(FIXTURE)))
    resume = asyncio.run(ResumeEnrichmentService().enrich(doc))
    return doc, resume


def test_sections_detected_without_false_headers(parsed):
    doc, _ = parsed
    names = set(doc.sections)
    assert "TECHNICAL SKILLS" in names
    assert "WORK EXPERIENCE" in names
    # A bold mixed-case project title must NOT be promoted to a section header...
    assert "Realtime Analytics Dashboard" not in names
    # ...and the PROJECTS section should therefore keep its content.
    projects = next((n for n in names if "PROJECT" in n.upper()), None)
    assert projects is not None
    assert len(doc.sections[projects].lines) > 0


def test_skills_are_clean(parsed):
    _, resume = parsed
    names = {s.name.lower() for s in resume.skills}
    # Real skills present, including a slash token kept intact.
    assert {"python", "c++", "go", "aws", "docker", "git", "ci/cd"} <= names
    # Category labels and punctuation artefacts absent.
    for junk in ("languages", "cloud & tools", "backend & architecture", "bash."):
        assert junk not in names
    # Parenthetical was not shredded.
    assert "aws (compute" not in names
    assert "networking)" not in names


def test_experience_fields_are_separated(parsed):
    _, resume = parsed
    assert len(resume.work_ex) == 3

    by_company = {j.company: j for j in resume.work_ex}
    # Each employer parsed cleanly from its own combined header line (incl. the
    # tab-separated one for Initech).
    assert any("Globex" in c for c in by_company)
    assert any("Initech" in c for c in by_company)
    assert any("Umbrella" in c for c in by_company)

    for job in resume.work_ex:
        assert job.duration != "Unknown"
        # Title/company/dates must not be mashed together.
        assert not re.search(r"\d{4}", job.title)
        assert not re.search(r"\d{4}", job.company)
        assert job.company not in job.title
