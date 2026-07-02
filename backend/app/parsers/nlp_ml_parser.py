import pdfplumber
import spacy
from sklearn.pipeline import Pipeline
from ..parsers import ParserInterface
from ..models.experience import Experience
from ..models.skill import Skill
from ..models.parsed_document import ParsedDocument
from ..core.logging import AppLogger

nlp = spacy.load("en_core_web_sm")
logger = AppLogger("NLPMLParser")


class NLPMLParser(ParserInterface):
    def __init__(self, ml_model: Pipeline):
        self.ml_model = ml_model

    async def parse(self, file_path: str) -> ParsedDocument:
        from app.models.document_section import DocumentSection
        import os, time

        logger.info(f"NLP/ML parsing of file: {file_path}")
        text = self.extract_text_from_pdf(file_path)
        extracted_info = self.extract_information(text)

        metadata = {
            "file_name": os.path.basename(file_path),
            "file_size": os.path.getsize(file_path),
            "last_modified": time.ctime(os.path.getmtime(file_path))
        }

        from app.models.document_section import DocumentSection
        from app.models.document_line import DocumentLine

        sections = {}
        for section_name, content_list in extracted_info.items():
            lines = [DocumentLine(text=line) for line in content_list]
            content = "\n".join(content_list)
            sections[section_name] = DocumentSection(name=section_name, lines=lines, content=content)

        parsed_document = ParsedDocument(
            metadata=metadata,
            sections=sections
        )

        return parsed_document

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        text = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text

    def extract_information(self, text: str) -> dict:
        import spacy
        doc = nlp(text)
        extracted_info = {
            "work_experience": [],
            "education": [],
            "skills": [],
            "summary": [],
            "contact": []
        }
        for sent in doc.sents:
            prediction = self.ml_model.predict([sent.text])[0]
            extracted_info[prediction].append(sent.text)
        return extracted_info
