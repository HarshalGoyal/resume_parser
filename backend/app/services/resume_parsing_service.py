import json

from app.core.logging import AppLogger

from app.ai.parsers.pdf_parser import PDFParser
from app.models.resume_processing_stages import ResumeProcessingStages
from app.storage.session_repository import SessionRepository
from app.storage.file_store import FileStore

class ResumeParsingService:
    def __init__(self):
        self.loggr = AppLogger("ResumeParsingService")
        self.loggr.info("Initialized ResumeParsingService for handling resume parsing logic.")
        
        self.Parser = PDFParser ()
        self.session_respositroy = SessionRepository ()
        self.file_store = FileStore ()

    async def parse_resume(self, file_path: str, session_id : str, upload_id : str):
        self.loggr.info(f"Parsing file_id: {upload_id}")
        await self.session_respositroy.update_stage (session_id= session_id, upload_id= upload_id,
                                                     stage=ResumeProcessingStages.PARSING)
        
        parsed_document = await self.Parser.parse (file_path)
        
        parsed_json = parsed_document.model_dump(mode="json")
        
        self.file_store.save_json (session_id=session_id, uploaded_file_id=upload_id,
                                   file_name="document_tree.json",data=parsed_json)
        
        await self.session_respositroy.update_stage (session_id=session_id, upload_id=upload_id,
                                                     stage= ResumeProcessingStages.DOC_TREE_GENERATEED)
        
        self.loggr.debug(f"Finished parsing file id: {upload_id}")
        self.loggr.debug(f"The parsed resume json object: {parsed_json} ")
        self.loggr.info (f"File {upload_id} parsed successfully")
        return parsed_json
        
    
