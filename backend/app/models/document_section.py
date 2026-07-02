from pydantic import BaseModel
from app.core.logging import AppLogger
from app.models.document_line import DocumentLine

Logger = AppLogger("DocumentSectionModel")
Logger.info("Initialized DocumentSection model for representing sections in a document.")

class DocumentSection(BaseModel):
    
    name: str
    content: str
    lines: list[DocumentLine]
    