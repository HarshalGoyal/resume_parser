import json

from ..models.resume_processing_stages import ResumeProcessingStages

from app.config.parser_config import get_selected_parser, ParserType
from app.parsers.rule_based_parser import RuleBasedParser
from app.parsers.nlp_ml_parser import NLPMLParser
from app.nlp.resume_nlp_parser import train_ml_model
from app.services.resume_enrichment_service import ResumeEnrichmentService
from app.storage.session_repository import SessionRepository
from app.storage.file_store import FileStore
from app.core.logging import AppLogger
from app.models.resume_processing_stages import ResumeProcessingStages

class ResumeParsingService:
    def __init__(self):
        self.loggr = AppLogger("ResumeParsingService")
        self.loggr.info("Initialized ResumeParsingService")
        self.session_respositroy = SessionRepository()
        self.file_store = FileStore()
        self.resume_enrichment_service = ResumeEnrichmentService()
        selected_parser = get_selected_parser()
        if selected_parser == ParserType.NLP_ML:
            ml_model = train_ml_model()
            self.parser = NLPMLParser(ml_model)
        else:
            self.parser = RuleBasedParser()

    async def parse_resume(self, file_path: str, session_id: str, upload_id: str):
        self.loggr.info(f"Parsing file_id: {upload_id}")
        await self.session_respositroy.update_stage(session_id=session_id, upload_id=upload_id, stage=ResumeProcessingStages.PARSING)

        parsed_document = await self.parser.parse(file_path)

        resume_document = await self.resume_enrichment_service.enrich(parsed_document)

        parsed_json = parsed_document.model_dump(mode="json")
        self.file_store.save_json(session_id=session_id, uploaded_file_id=upload_id, file_name="document_tree.json", data=parsed_json)

        await self.session_respositroy.update_stage(session_id=session_id, upload_id=upload_id, stage=ResumeProcessingStages.DOC_TREE_GENERATEED)
        parsed_resume_json = resume_document.model_dump(mode="json")
        self.file_store.save_json(session_id=session_id, uploaded_file_id=upload_id, file_name="resume_extracted.json", data=parsed_resume_json)

        await self.session_respositroy.update_stage(session_id=session_id, upload_id=upload_id, stage=ResumeProcessingStages.PARSED)

        self.loggr.debug(f"Finished parsing file id: {upload_id}")
        self.loggr.info(f"File {upload_id} parsed successfully")
        return parsed_resume_json


        