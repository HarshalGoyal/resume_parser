"""Generic, format-agnostic text helpers used by parsers and enrichment.

These are deliberately layout/convention based (whitespace, casing, common
resume section vocabulary, generic org/date markers) rather than tuned to any
single document, so they generalize across arbitrary resumes.
"""

import re


# Broad set of section titles seen across resumes. Matched as whole words so a
# bullet mentioning "experience" in prose does not become a section header.
SECTION_KEYWORDS = [
    "summary", "objective", "profile", "about",
    "experience", "employment", "work history", "professional experience",
    "education", "academics", "qualifications",
    "skills", "technical skills", "core competencies", "competencies",
    "expertise", "technologies", "tech stack", "tools",
    "projects", "personal projects", "open source", "open-source",
    "certifications", "certificates", "licenses",
    "publications", "research",
    "achievements", "awards", "honors",
    "languages", "interests", "hobbies",
    "volunteer", "leadership", "activities",
    "contact", "references",
]

_SECTION_KEYWORD_RE = re.compile(
    r"^\W*(?:" + "|".join(re.escape(k) for k in SECTION_KEYWORDS) + r")\b",
    re.IGNORECASE,
)

# Generic organisation markers (legal suffixes / common company words). Used to
# locate a company name inside a combined "Title  Company  Dates" line when the
# layout gap heuristic is unavailable. Not tied to any specific employer.
ORG_MARKERS = [
    "inc", "inc.", "llc", "ltd", "ltd.", "limited", "pvt", "pvt.",
    "corp", "corp.", "co", "co.", "gmbh", "s.a.", "plc", "ag", "srl",
    "technologies", "solutions", "systems", "labs", "software", "services",
    "consulting", "group", "holdings", "industries", "enterprises",
    "university", "institute", "college", "school", "foundation",
]

_BULLET_RE = re.compile(r"^\s*[•●◦‣⁃\-\*·o]\s+")
_MULTISPACE_RE = re.compile(r"\s{2,}")
_WS_RE = re.compile(r"\s+")


def collapse_whitespace(text: str) -> str:
    """Collapse all runs of whitespace to a single space and trim."""
    return _WS_RE.sub(" ", text).strip()


def split_layout_segments(raw: str) -> list[str]:
    """Split a line into visual segments on runs of 2+ spaces or tabs.

    Multi-space / tab gaps are how most resumes visually separate columns such
    as ``Title      Company      Dates`` on one line. Single spaces inside a
    field are preserved. Returns the non-empty, trimmed segments.
    """
    normalized = raw.replace("\t", "   ")
    segments = _MULTISPACE_RE.split(normalized.strip())
    return [collapse_whitespace(s) for s in segments if s.strip()]


def looks_like_section_header(text: str) -> bool:
    """Heuristically decide whether a short line is a section title.

    Generic signals only: a leading known section keyword, or an all-caps short
    line (a near-universal resume convention). Length-bounded so sentences and
    bullets are excluded.
    """
    stripped = text.strip()
    if not stripped or len(stripped) > 60:
        return False
    # "Label: value" lines (e.g. "Languages: C++, Python") are content, not
    # section titles, even when the label matches a section keyword.
    if ":" in stripped and stripped.split(":", 1)[1].strip():
        return False
    if _SECTION_KEYWORD_RE.match(stripped):
        return True
    letters = [c for c in stripped if c.isalpha()]
    if letters and all(c.isupper() for c in letters) and len(letters) >= 2:
        return True
    return False


def strip_bullet(text: str) -> str:
    """Remove a leading bullet/list marker from a line."""
    return _BULLET_RE.sub("", text).strip()


def split_top_level(text: str) -> list[str]:
    """Split on commas/semicolons/pipes/newlines that are NOT inside brackets.

    Keeps parenthesised qualifiers intact, e.g. ``AWS (Compute, Networking)``
    stays a single token instead of being shredded on its inner comma. Does not
    split on "/" so tokens like ``CI/CD`` and ``TCP/IP`` survive intact.
    """
    parts: list[str] = []
    depth = 0
    current = []
    for ch in text:
        if ch in "([{":
            depth += 1
            current.append(ch)
        elif ch in ")]}":
            depth = max(0, depth - 1)
            current.append(ch)
        elif ch in ",;|\n" and depth == 0:
            parts.append("".join(current))
            current = []
        else:
            current.append(ch)
    parts.append("".join(current))
    return [p.strip() for p in parts if p.strip()]


def clean_skill_token(token: str) -> str:
    """Normalise a raw skill token into a clean skill name.

    Drops a trailing parenthetical qualifier, strips surrounding punctuation and
    stray brackets, collapses whitespace. Returns "" if nothing usable remains.
    """
    # Drop a trailing "(...)" qualifier: "AWS (Compute, Networking)" -> "AWS".
    token = re.sub(r"\s*\([^)]*\)\s*$", "", token)
    token = token.strip().strip(".,;:•|/\\()[]{}").strip()
    return collapse_whitespace(token)
