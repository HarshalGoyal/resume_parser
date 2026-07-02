"""Enrichment tests over synthetic documents (not the sample resume).

Uses invented companies, titles and multiple date formats so the tests assert
generic behaviour rather than anything specific to one file.
"""

import asyncio

from app.models.document_line import DocumentLine
from app.models.document_section import DocumentSection
from app.models.parsed_document import ParsedDocument
from app.services.resume_enrichment_service import ResumeEnrichmentService


def _doc(sections: dict[str, list[DocumentLine]]) -> ParsedDocument:
    built = {
        name: DocumentSection(
            name=name,
            content="\n".join(l.text for l in lines),
            lines=lines,
        )
        for name, lines in sections.items()
    }
    return ParsedDocument(metadata={}, sections=built)


def _enrich(doc):
    return asyncio.run(ResumeEnrichmentService().enrich(doc))


# --- Skills ---------------------------------------------------------------

def test_skills_drop_category_labels_and_punctuation():
    doc = _doc(
        {
            "TECHNICAL SKILLS": [
                DocumentLine(text="Languages: C++, Python, Go."),
                DocumentLine(text="Cloud & Tools: AWS (Compute, Networking), Git."),
            ]
        }
    )
    names = {s.name.lower() for s in _enrich(doc).skills}
    assert {"c++", "python", "go", "aws", "git"} <= names
    # Category labels and punctuation artefacts must NOT appear.
    assert "languages" not in names
    assert "cloud & tools" not in names
    assert "go." not in names
    assert "aws (compute" not in names
    assert "networking)" not in names


def test_skills_deduplicated_case_insensitively():
    doc = _doc(
        {
            "Skills": [
                DocumentLine(text="Python, python, PYTHON"),
            ]
        }
    )
    assert len(_enrich(doc).skills) == 1


# --- Experience -----------------------------------------------------------

def _header(title, company, dates):
    """A job header line laid out as three gap-separated columns."""
    text = f"{title}      {company}      {dates}"
    return DocumentLine(text=text, segments=[title, company, dates])


def test_experience_layout_columns_split_cleanly():
    doc = _doc(
        {
            "WORK EXPERIENCE": [
                _header("Staff Engineer", "Globex Corp", "Jan 2021 - Present"),
                DocumentLine(text="• Led the payments platform rewrite."),
                DocumentLine(text="• Cut p99 latency by 40%."),
                _header("Backend Engineer", "Initech LLC", "Jun 2018 - Dec 2020"),
                DocumentLine(text="• Built the billing service."),
            ]
        }
    )
    ex = _enrich(doc).work_ex
    assert len(ex) == 2
    assert ex[0].title == "Staff Engineer"
    assert ex[0].company == "Globex Corp"
    assert "Jan 2021 - Present" in ex[0].duration
    assert "payments platform" in ex[0].description
    # Company must not leak from a bullet or the previous job.
    assert ex[1].title == "Backend Engineer"
    assert ex[1].company == "Initech LLC"
    assert "2018" in ex[1].duration


def test_experience_title_comma_company_fallback():
    # No layout gaps; single field uses the "Title, Company" convention.
    doc = _doc(
        {
            "Employment": [
                DocumentLine(
                    text="Data Scientist, Umbrella Inc 03/2019 - 05/2022",
                    segments=[],
                ),
                DocumentLine(text="- Shipped fraud models."),
            ]
        }
    )
    ex = _enrich(doc).work_ex
    assert len(ex) == 1
    assert ex[0].title == "Data Scientist"
    assert ex[0].company.startswith("Umbrella Inc")
    assert "2019" in ex[0].duration


def test_bold_bullets_do_not_become_company():
    # Bullets marked bold must never be treated as company/header.
    doc = _doc(
        {
            "Experience": [
                _header("SRE", "Hooli", "2020 - 2023"),
                DocumentLine(text="Improved uptime to 99.99%.", bold=True),
                DocumentLine(text="Owned the on-call rotation.", bold=True),
            ]
        }
    )
    ex = _enrich(doc).work_ex
    assert len(ex) == 1
    assert ex[0].company == "Hooli"
    assert "uptime" in ex[0].description


# --- Contact --------------------------------------------------------------

def test_contact_extraction_dedupes():
    doc = _doc(
        {
            "HEADER": [
                DocumentLine(text="jane@example.com jane@example.com"),
                DocumentLine(text="github.com/jane linkedin.com/in/jane"),
            ]
        }
    )
    info = _enrich(doc).contact_info
    assert info.emails == ["jane@example.com"]
    assert any("github.com/jane" in g for g in info.github_profiles)
    assert any("linkedin.com/in/jane" in l for l in info.linkedin_profiles)
