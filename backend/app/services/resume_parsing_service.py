import asyncio

from app.ai.parsers.pdf_parser import PDFParser
from app.ai.parsers.docx_parser import DOCXParser
from app.core.exceptions import InvalidFileFormatError
from app.models.resume_processing_stages import ResumeProcessingStages
from app.services.resume_enrichment_service import ResumeEnrichmentService
from app.storage.session_repository import SessionRepository
from app.storage.file_store import FileStore
from app.core.logging import AppLogger


class ResumeParsingService:
    def __init__(self, session_repository: SessionRepository | None = None):
        self.logger = AppLogger("ResumeParsingService")
        self.logger.info("Initialized ResumeParsingService for resume parsing.")

        # Strategy registry keyed by canonical file type; both parsers return
        # the same ParsedDocument shape so enrichment is format-agnostic.
        self.parsers = {"pdf": PDFParser(), "docx": DOCXParser()}
        # Reuse the caller's repository so cache + stage updates stay consistent
        # across the upload and parsing paths; fall back to a fresh one for
        # standalone use (e.g. tests).
        self.session_repository = session_repository or SessionRepository()
        self.file_store = FileStore()
        self.resume_enrichment_service = ResumeEnrichmentService()

    async def parse_resume(
        self, file_path: str, session_id: str, upload_id: str, file_type: str
    ):
        self.logger.info(f"Parsing upload_id: {upload_id} (type={file_type})")
        parser = self.parsers.get(file_type)
        if parser is None:
            raise InvalidFileFormatError(file_path=file_path, file_type=file_type)

        await self.session_repository.update_stage(
            session_id=session_id,
            upload_id=upload_id,
            stage=ResumeProcessingStages.PARSING,
        )

        parsed_document = await parser.parse(file_path)
        resume_document = await self.resume_enrichment_service.enrich(parsed_document)

        await asyncio.to_thread(
            self.file_store.save_json,
            session_id=session_id,
            uploaded_file_id=upload_id,
            file_name="document_tree.json",
            data=parsed_document.model_dump(mode="json"),
        )
        await self.session_repository.update_stage(
            session_id=session_id,
            upload_id=upload_id,
            stage=ResumeProcessingStages.DOC_TREE_GENERATED,
        )

        parsed_resume_json = resume_document.model_dump(mode="json")
        await asyncio.to_thread(
            self.file_store.save_json,
            session_id=session_id,
            uploaded_file_id=upload_id,
            file_name="resume_extracted.json",
            data=parsed_resume_json,
        )
        await self.session_repository.update_stage(
            session_id=session_id,
            upload_id=upload_id,
            stage=ResumeProcessingStages.PARSED,
        )

        self.logger.info(f"File {upload_id} parsed successfully")
        return parsed_resume_json
