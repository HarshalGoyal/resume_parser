from pydantic import BaseModel
from app.core.logging import AppLogger
from app.models.document_line import DocumentLine
from app.models.document_section import DocumentSection
from app.models.contact_info import ContactInfo

Logger = AppLogger("ParsedDocumentModel")
Logger.info("Initialized ParsedDocument model for representing the overall structure of a parsed document.")

class ParsedDocument(BaseModel):
    
    metadata : dict
    sections: dict[str,DocumentSection]