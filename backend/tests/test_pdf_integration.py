"""Integration test: parse the synthetic sample resume PDF end to end.

The fixture (backend/tests/fixtures/sample_resume.pdf) uses fake data but
reproduces the PDF-specific challenges seen in real resumes: Title/Company/Dates
laid out as columns on one line (wide space gaps), a date placed on its own
line, a skills phrase that wraps across two lines, and lone bullet glyphs on
their own lines. The logic under test stays generic (no fixture-specific
strings baked in).
"""

import asyncio
import re
from pathlib import Path

import pytest

from app.ai.parsers.pdf_parser import PDFParser
from app.services.resume_enrichment_service import ResumeEnrichmentService

FIXTURE = Path(__file__).parent / "fixtures" / "sample_resume.pdf"


@pytest.fixture(scope="module")
def parsed():
    doc = asyncio.run(PDFParser().parse(str(FIXTURE)))
    resume = asyncio.run(ResumeEnrichmentService().enrich(doc))
    return doc, resume


def test_sections_detected_without_false_headers(parsed):
    doc, _ = parsed
    names = set(doc.sections)
    assert "TECHNICAL SKILLS" in names
    assert "WORK EXPERIENCE" in names
    # A bold mixed-case project title must NOT become a section header.
    assert "Realtime Analytics Dashboard" not in names
    projects = next((n for n in names if "PROJECT" in n.upper()), None)
    assert projects is not None
    assert len(doc.sections[projects].lines) > 0


def test_skills_clean_and_wrapped_phrase_rejoined(parsed):
    _, resume = parsed
    names = {s.name.lower() for s in resume.skills}
    assert {"python", "c++", "go", "aws", "docker", "git", "ci/cd"} <= names
    # A phrase that wrapped across two PDF lines must be a single skill...
    assert "low level socket programming" in names
    # ...not two fragments.
    assert "low level socket" not in names
    assert "programming" not in names
    # No category labels or punctuation artefacts.
    assert "languages" not in names
    assert "bash." not in names


def test_experience_columns_and_split_date_line(parsed):
    _, resume = parsed
    assert len(resume.work_ex) == 3

    companies = {j.company for j in resume.work_ex}
    assert companies == {"Globex Corporation", "Initech LLC", "Umbrella Inc"}

    by_company = {j.company: j for j in resume.work_ex}
    assert by_company["Globex Corporation"].title == "Senior Software Engineer"
    # Job whose date was on its own line still gets its duration.
    assert by_company["Initech LLC"].title == "Backend Engineer"
    assert "2019" in by_company["Initech LLC"].duration

    for job in resume.work_ex:
        assert job.duration != "Unknown"
        # Fields must be cleanly separated — no dates leaking into title/company.
        assert not re.search(r"\d{4}", job.title)
        assert not re.search(r"\d{4}", job.company)
        # Lone bullet glyphs must not survive as description content.
        assert "·" not in job.description
        assert "•" not in job.description


def test_contact_extracted(parsed):
    _, resume = parsed
    assert "jordan.dev@example.com" in resume.contact_info.emails
    assert any("github.com/jordandev" in g for g in resume.contact_info.github_profiles)
