import fitz
import re
from typing import Optional, Dict
from app.models.pared_document import ParsedDocument
from app.models.document_line import DocumentLine
from app.models.document_section import DocumentSection


from app.core.logging import AppLogger

class PDFParser:
    def __init__(self):
        self.loggr = AppLogger("PDFParser")
        self.loggr.info("Initialized PDFParser class for handling PDF parsing logic.")

    async def parse(self, file_path: str) -> ParsedDocument:
        
        self.loggr.info(f"Parsing PDF at path: {file_path}")
        doc = fitz.open(file_path)
        parsed_lines = []
        
        for page_ndx, page in enumerate(doc):
            
            raw_dict = page.get_text("rawdict")
            
            page_links = self.__extract_links(page)
            
            for block in raw_dict["blocks"]:
                
                if block["type"] != 0:  # non text block
                    continue                    
                for line in block["lines"]:
                    parsed_line = self.__parse_line(line,page_ndx,page_links)
                    
                    if parsed_line is not None:
                        parsed_lines.append(parsed_line)
                        
        self.__detect_headers(parsed_lines)
        sections = self.__build_sections (parsed_lines)
        
        self.loggr.info (f"parsed {len(sections)} sections in this page")
        
        return ParsedDocument (metadata = {"pages": len(doc)}, sections = sections)
    
    def __extract_links (self, page) -> list[dict]:
        
        page_links = []
        
        for link in page.get_links():
            if "uri" not in link:
                continue
            
            page_links.append ({"rect" : fitz.Rect(link["from"]), "url" : link["uri"] })
        return page_links
    
    def __parse_line (self,line,page_index,page_links) -> Optional[DocumentLine]:
        
        line_text = ""
        max_font_size = 0
        bold = False
        fonts = set()
        line_rect = fitz.Rect (line["bbox"])
        
        for span in line["spans"]:
            
            span_text = (self.__extract_span_text(span))            
            line_text += span_text
            max_font_size = max(max_font_size, span["size"])
            fonts.add(span["font"])
            
            if (self.__is_bold(span["font"])):
                bold = True
                
        line_text = self.__normalize_text (line_text)
        
        if not line_text:
            return None

        matched_links = []
        
        for link in page_links:
            
            if line_rect.intersects(link["rect"]):
                matched_links.append(link["url"])
        
        return DocumentLine(text=line_text,font_size=round(max_font_size, 2),
                            bold=bold,fonts=list(fonts),bbox=list(line["bbox"]),
                            page=page_index + 1,links=matched_links)
    
    
    def __detect_headers(self,parsed_lines) -> None:
        
        avg_font_size = (sum(line.font_size for line in parsed_lines) / len(parsed_lines))

        for line in parsed_lines:

            line.is_header = (line.font_size > avg_font_size + 1 
                                        and
                              line.bold and len(line.text) < 50)
        
    def __build_sections(self,parsed_lines) -> Dict[str,DocumentSection]:

        sections = {}
        current_section = "HEADER"
        sections[current_section] = []
        
        for line in parsed_lines:
            
            if line.is_header:
                current_section = line.text
                if current_section not in sections:
                    sections[current_section] = []
                continue
            sections[current_section].append(line)

        structured_sections = {}

        for section_name,lines in sections.items():

            structured_sections[section_name] = DocumentSection( name=section_name,
                                                                content="\n".join(line.text for line in lines),
                                                                lines=lines)
        return structured_sections
    
    def __extract_span_text(self,span) -> str:
        if "text" in span:
            return span["text"]
        if "chars" in span:
            return "".join(ch["c"] for ch in span["chars"])
        return ""

    def __is_bold(self,font_name: str) -> bool:

        font_name = font_name.lower()
        
        return any(x in font_name
                     for x in ["bold","black","heavy","semibold"]
                )

    def __normalize_text (self,text : str) -> str :
        text = re.sub(r"\s+"," ", text)
        return text.strip()
