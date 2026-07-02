from typing import TYPE_CHECKING
from ..parsers import ParserInterface
from ..models.parsed_document import ParsedDocument
from ..ai.parsers.pdf_parser import PDFParser
from ..core.logging import AppLogger

if TYPE_CHECKING:
    pass

logger = AppLogger("RuleBasedParser")


class RuleBasedParser(ParserInterface):
    def __init__(self):
        self.parser = PDFParser()

    async def parse(self, file_path: str) -> ParsedDocument:
        logger.info(f"Rule-based parsing of file: {file_path}")
        parsed_document = await self.parser.parse(file_path)
        return parsed_document
