import re
from typing import Dict

from docx import Document

from app.models.parsed_document import ParsedDocument
from app.models.document_line import DocumentLine
from app.models.document_section import DocumentSection
from app.core.logging import AppLogger


class DOCXParser:
    """Structural parser for .docx resumes.

    Produces the same ``ParsedDocument`` shape as ``PDFParser`` so the
    downstream enrichment service is agnostic to the source format. Section
    headers are inferred from Word heading styles or fully-bold short
    paragraphs (the DOCX analogue of the PDF font-size/bold heuristic).
    """

    def __init__(self):
        self.logger = AppLogger("DOCXParser")
        self.logger.info("Initialized DOCXParser for handling DOCX parsing logic.")

    async def parse(self, file_path: str) -> ParsedDocument:
        self.logger.info(f"Parsing DOCX at path: {file_path}")
        document = Document(file_path)

        parsed_lines: list[DocumentLine] = []
        for paragraph in document.paragraphs:
            text = self.__normalize_text(paragraph.text)
            if not text:
                continue
            parsed_lines.append(
                DocumentLine(
                    text=text,
                    bold=self.__is_bold(paragraph),
                    is_header=self.__is_header(paragraph),
                )
            )

        sections = self.__build_sections(parsed_lines)
        self.logger.info(f"parsed {len(sections)} sections from DOCX")
        return ParsedDocument(metadata={"paragraphs": len(parsed_lines)}, sections=sections)

    def __is_header(self, paragraph) -> bool:
        style_name = (paragraph.style.name or "").lower() if paragraph.style else ""
        if style_name.startswith("heading") or style_name == "title":
            return True
        # A short, fully-bold standalone line is treated as a section header.
        text = paragraph.text.strip()
        return bool(text) and len(text) < 50 and self.__is_bold(paragraph, require_all=True)

    def __is_bold(self, paragraph, require_all: bool = False) -> bool:
        runs = [r for r in paragraph.runs if r.text.strip()]
        if not runs:
            return False
        flags = [bool(r.bold) for r in runs]
        return all(flags) if require_all else any(flags)

    def __build_sections(self, parsed_lines) -> Dict[str, DocumentSection]:
        sections: dict[str, list[DocumentLine]] = {"HEADER": []}
        current_section = "HEADER"

        for line in parsed_lines:
            if line.is_header:
                current_section = line.text
                sections.setdefault(current_section, [])
                continue
            sections[current_section].append(line)

        return {
            name: DocumentSection(
                name=name,
                content="\n".join(line.text for line in lines),
                lines=lines,
            )
            for name, lines in sections.items()
        }

    def __normalize_text(self, text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()
