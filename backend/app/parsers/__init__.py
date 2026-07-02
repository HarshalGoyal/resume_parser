from abc import ABC, abstractmethod
from typing import Protocol

from ..models.parsed_document import ParsedDocument


class ParserInterface(ABC):
    @abstractmethod
    async def parse(self, file_path: str) -> ParsedDocument:
        pass


class ParserProtocol(Protocol):
    async def parse(self, file_path: str) -> ParsedDocument:
        ...
