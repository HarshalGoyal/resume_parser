import re

from app.core.logging import AppLogger
from app.models.parsed_document import ParsedDocument
from app.models.contact_info import ContactInfo
from app.models.skill import Skill
from app.models.experience import Experience
from app.models.resume_document import ResumeDocument
from app.utils.text_utils import (
    collapse_whitespace,
    split_top_level,
    clean_skill_token,
    strip_bullet,
)

LINKEDIN_REGEX = r"(?:https?://)?(?:www\.)?linkedin\.com/[A-Za-z0-9\-_/]+"
GITHUB_REGEX = r"(?:https?://)?(?:www\.)?github\.com/[A-Za-z0-9\-_]+"
URL_REGEX = r"https?://[^\s]+"

SKILLS_SECTION_REGEX = re.compile(
    r"\b(skill|skills|tech stack|technolog(?:y|ies)|expertise|"
    r"core competenc(?:y|ies)|competenc(?:y|ies)|tools|proficienc(?:y|ies))\b",
    re.IGNORECASE,
)
EXPERIENCE_SECTION_REGEX = re.compile(
    r"(experience|employment|work history)", re.IGNORECASE
)

# --- Generic date detection (template independent) -------------------------
_MONTH = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sept?|Oct|Nov|Dec)[a-z]*\.?"
_YEAR = r"\d{4}"
_DATE_POINT = rf"(?:{_MONTH}\s+{_YEAR}|\d{{1,2}}[/-]{_YEAR}|{_YEAR})"
_PRESENT = r"(?:Present|Current|Now|Ongoing|Till\s+Date|To\s+Date)"
# A full range like "Jan 2020 - Mar 2021", "2019 – 2021", "03/2020 to Present".
DATE_RANGE_REGEX = re.compile(
    rf"{_DATE_POINT}\s*(?:[-–—]|to)\s*(?:{_DATE_POINT}|{_PRESENT})", re.IGNORECASE
)
# A range OR a lone "Month Year" — used to recognise a job header line. A bare
# year on its own is intentionally NOT enough (bullets can mention a year).
DATE_HEADER_REGEX = re.compile(
    rf"(?:{_DATE_POINT}\s*(?:[-–—]|to)\s*(?:{_DATE_POINT}|{_PRESENT})|{_MONTH}\s+{_YEAR})",
    re.IGNORECASE,
)


class ResumeEnrichmentService:

    def __init__(self) -> None:
        self.logger = AppLogger("ResumeEnrichmentService")

    async def enrich(self, parsed_doc: ParsedDocument) -> ResumeDocument:
        self.logger.info("Enriching parsed document")
        full_text = self.__build_full_text(parsed_doc)
        contact_info = self.__extract_contact_info(full_text)
        skills = self.__extract_skills(parsed_doc)
        work_ex = self.__extract_work_ex(parsed_doc)
        return ResumeDocument(
            contact_info=contact_info, skills=skills, work_ex=work_ex
        )

    def __extract_contact_info(self, text: str) -> ContactInfo:
        emails = self.__unique(
            re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
        )
        phones = self.__unique(re.findall(r"\+?\d[\d\s\-()]{8,}\d", text))
        linkedin = self.__unique(re.findall(LINKEDIN_REGEX, text, re.IGNORECASE))
        github = self.__unique(re.findall(GITHUB_REGEX, text, re.IGNORECASE))
        other_links = self.__unique(re.findall(URL_REGEX, text, re.IGNORECASE))
        return ContactInfo(
            emails=emails,
            phone_numbers=phones,
            linkedin_profiles=linkedin,
            github_profiles=github,
            other_links=other_links,
        )

    def __extract_skills(self, parsed_document: ParsedDocument) -> list[Skill]:
        seen: dict[str, Skill] = {}

        for section_name, section in parsed_document.sections.items():
            if not SKILLS_SECTION_REGEX.search(section_name):
                continue

            line_texts = [
                line.text for line in section.lines
            ] or section.content.split("\n")
            # Rejoin lines that wrapped mid-list (common in PDFs) so a token like
            # "Low level socket programing" is not split across two entries.
            for group in self.__group_skill_lines(line_texts):
                # Drop a leading "Category:" label, keep only the list to its right.
                if ":" in group:
                    group = group.split(":", 1)[1]
                for raw_token in split_top_level(group):
                    name = clean_skill_token(raw_token)
                    if not name or not any(c.isalnum() for c in name):
                        continue
                    key = name.lower()
                    if key not in seen:
                        seen[key] = Skill(name=name)

        return list(seen.values())

    @staticmethod
    def __group_skill_lines(line_texts: list[str]) -> list[str]:
        """Merge wrapped continuation lines into their "Category:" line.

        A line beginning with a short "Label:" is a new group; any following line
        without such a label is a wrap of the previous line and is appended.
        """
        label_re = re.compile(r"^\s*[^:\n]{1,40}:\s*\S")
        groups: list[str] = []
        for text in line_texts:
            if not text.strip():
                continue
            if label_re.match(text) or not groups:
                groups.append(text.strip())
            else:
                groups[-1] = f"{groups[-1]} {text.strip()}"
        return groups

    def __extract_work_ex(self, parsed_document: ParsedDocument) -> list[Experience]:
        experiences: list[Experience] = []

        for section_name, section in parsed_document.sections.items():
            if not EXPERIENCE_SECTION_REGEX.search(section_name):
                continue

            current: dict | None = None
            # Combine a date that was laid out on its own line with the title
            # line above it (common in PDFs) so each job header carries its date.
            for text, segments in self.__premerge_date_lines(section.lines):
                if not text:
                    continue

                if DATE_HEADER_REGEX.search(text):
                    # Start of a new job entry — flush the previous one first.
                    if current is not None:
                        experiences.append(self.__to_experience(current))
                    title, company, duration = self.__parse_header(text, segments)
                    current = {
                        "title": title,
                        "company": company,
                        "duration": duration,
                        "description": [],
                    }
                    continue

                if current is not None:
                    cleaned = strip_bullet(text)
                    # Skip lines that are only a bullet/marker glyph (PDFs often
                    # emit the bullet as its own line).
                    if self.__is_marker_only(text) or not cleaned:
                        continue
                    current["description"].append(cleaned)

            if current is not None:
                experiences.append(self.__to_experience(current))

        return experiences

    def __premerge_date_lines(self, lines) -> list[tuple[str, list[str]]]:
        """Return (text, segments) pairs, merging a standalone date line into the
        preceding line so it becomes a complete job header."""
        result: list[tuple[str, list[str]]] = []
        for line in lines:
            text = line.text.strip()
            if not text:
                continue
            segments = [s for s in (line.segments or []) if s]
            if self.__is_date_only(text) and result:
                prev_text, prev_segments = result[-1]
                merged_segments = (prev_segments or [prev_text]) + [text]
                result[-1] = (f"{prev_text}   {text}", merged_segments)
            else:
                result.append((text, segments))
        return result

    @staticmethod
    def __is_date_only(text: str) -> bool:
        match = DATE_RANGE_REGEX.search(text) or DATE_HEADER_REGEX.search(text)
        if not match:
            return False
        residual = collapse_whitespace(text.replace(match.group(0), ""))
        return len(residual) <= 2

    @staticmethod
    def __is_marker_only(text: str) -> bool:
        return not re.sub(r"[•●◦‣⁃·*\-\s]", "", text)

    def __parse_header(
        self, text: str, segments: list[str]
    ) -> tuple[str | None, str | None, str | None]:
        """Split a combined job-header line into (title, company, duration).

        Relies on visual layout segments (multi-space/tab gaps, or PDF column
        gaps) when available — the common "Title    Company    Dates"
        arrangement — and falls back to date-stripping + comma splitting when no
        gap structure exists.
        """
        match = DATE_RANGE_REGEX.search(text) or DATE_HEADER_REGEX.search(text)
        duration = match.group(0).strip() if match else None

        segments = [s for s in (segments or []) if s]
        non_date_segments = (
            [s for s in segments if not (match and match.group(0) in s)]
            if segments
            else []
        )

        title: str | None
        company: str | None
        if len(non_date_segments) >= 2:
            title = non_date_segments[0]
            company = " ".join(non_date_segments[1:])
        elif len(non_date_segments) == 1:
            title, company = self.__split_title_company(non_date_segments[0])
        else:
            remainder = (
                collapse_whitespace(text.replace(match.group(0), "")) if match else text
            )
            title, company = self.__split_title_company(remainder)

        return (title or None), (company or None), (duration or None)

    @staticmethod
    def __split_title_company(text: str) -> tuple[str | None, str | None]:
        text = text.strip(" ,–-|\t")
        if not text:
            return None, None
        # "Title, Company" is a very common single-field convention.
        if "," in text:
            head, _, tail = text.partition(",")
            return head.strip() or None, tail.strip() or None
        return text, None

    @staticmethod
    def __to_experience(entry: dict) -> Experience:
        return Experience(
            title=entry["title"] or "Unknown",
            company=entry["company"] or "Unknown",
            duration=entry["duration"] or "Unknown",
            description="\n".join(entry["description"]).strip(),
        )

    def __build_full_text(self, parsed_document: ParsedDocument) -> str:
        return "\n".join(
            section.content for section in parsed_document.sections.values()
        )

    @staticmethod
    def __unique(items: list[str]) -> list[str]:
        seen: dict[str, str] = {}
        for item in items:
            key = item.strip().lower()
            if key and key not in seen:
                seen[key] = item.strip()
        return list(seen.values())
