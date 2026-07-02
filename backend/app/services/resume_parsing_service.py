import json

from ..models.resume_processing_stages import ResumeProcessingStages

from app.ai.parsers.pdf_parser import PDFParser
from app.models.resume_processing_stages import ResumeProcessingStages
from app.services.resume_enrichment_service import ResumeEnrichmentService
from app.storage.session_repository import SessionRepository
from app.storage.file_store import FileStore
from app.core.logging import AppLogger
from app.models.resume_processing_stages import ResumeProcessingStages

class ResumeParsingService:
    def __init__(self):
        self.loggr = AppLogger("ResumeParsingService")
        self.loggr.info("Initialized ResumeParsingService for handling resume parsing logic.")
        
        self.Parser = PDFParser ()
        self.session_respositroy = SessionRepository ()
        self.file_store = FileStore ()
        self.resume_enrichment_service = ResumeEnrichmentService()

    async def parse_resume(self, file_path: str, session_id: str, upload_id: str):
        self.loggr.info(f"Parsing file_id: {upload_id}")
        await self.session_respositroy.update_stage (session_id= session_id, upload_id= upload_id,
                                                     stage=ResumeProcessingStages.PARSING)
        
        parsed_document = await self.Parser.parse (file_path)
        
        resume_document = await self.resume_enrichment_service.enrich(parsed_document)
           
        parsed_json = parsed_document.model_dump(mode="json")
        
        self.file_store.save_json (session_id=session_id, uploaded_file_id=upload_id,
                                   file_name="document_tree.json",data=parsed_json)
        
        await self.session_respositroy.update_stage (session_id=session_id, upload_id=upload_id,
                                                     stage= ResumeProcessingStages.DOC_TREE_GENERATEED)
        parsed_resume_json = resume_document.model_dump(mode="json")
        self.file_store.save_json(session_id=session_id, uploaded_file_id=upload_id,
                                  file_name="resume_extracted.json",data=parsed_resume_json)
        
        await self.session_respositroy.update_stage (session_id=session_id, upload_id=upload_id,
                                                     stage= ResumeProcessingStages.PARSED)
        self.loggr.debug(f"Finished parsing file id: {upload_id}")
        self.loggr.info (f"File {upload_id} parsed successfully")
        return parsed_resume_json
        
    
