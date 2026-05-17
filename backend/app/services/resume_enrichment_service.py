import re
from app.core.logging import AppLogger
from app.models.parsed_document import ParsedDocument
from app.models.contact_info import ContactInfo
from app.models.skill import Skill
from app.models.experience import Experience
from app.models.resume_document import ResumeDocument

LINKEDIN_REGEX = r"(?:https?://)?(?:www\.)?linkedin\.com/[A-Za-z0-9\-_/]+"
GITHUB_REGEX = r"(?:https?://)?(?:www\.)?github\.com/[A-Za-z0-9\-_]+"
URL_REGEX = r"https?://[^\s]+"

class ResumeEnrichmentService:
    
    def __init__(self) -> None:
        self.logger = AppLogger ("ResumeEnrichmentService")
        
    async def enrich (self, parsed_doc : ParsedDocument ) -> ResumeDocument:
        self.logger.info ("Enriching parsed document")
        full_text = self.__build_full_text(parsed_doc)
        contact_info = self.__extract_contact_info(full_text)
        skills = self.__extract_skills(parsed_doc)
        work_ex = self.__extract_work_ex(parsed_doc)
        return ResumeDocument(contact_info=contact_info, skills=skills, work_ex=work_ex)
        
    def __extract_contact_info(self, text:str) -> ContactInfo:
        
        emails = re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",text)
        phones = re.findall(r"\+?\d[\d\s\-()]{8,}\d", text)
        linkedin = re.findall(LINKEDIN_REGEX,text,re.IGNORECASE)
        github = re.findall(GITHUB_REGEX,text,re.IGNORECASE)
        other_links = re.findall(URL_REGEX,text,re.IGNORECASE)
        if len(other_links) < 1:
            other_links = []
            
        return ContactInfo(emails = emails, phone_numbers = phones,
                           linkedin_profiles = linkedin, github_profiles=github,
                           other_links = other_links)
    
    def __extract_skills(self, parsed_document : ParsedDocument) -> list[Skill]:
        
        SKILLS_SECTION_REGEX = r"\b(skill|skills|technical skills|tech stack|technologies|expertise|core competencies|competencies|tools)\b"
        extracted_skills = []
        
        for (section_name,section) in parsed_document.sections.items():
            
            if not re.search(SKILLS_SECTION_REGEX,section_name,re.IGNORECASE):
                continue
                
            tokens = re.split(r"[,\n|:/]+",section.content)
            
            for token in tokens:
                cleaned = token.strip().lower()

                if not cleaned:
                    continue
                if len(cleaned) < 2:
                    continue
                extracted_skills.append(Skill(name=cleaned))
        unique_skills = {}
        
        for skill in extracted_skills:
            unique_skills[skill.name.lower()] = skill
            
        return list(unique_skills.values())
    
    def __extract_work_ex(self,parsed_document: ParsedDocument) -> list[Experience]:

        EXPERIENCE_SECTION_REGEX = re.compile(r"(experience|employment|work history)",re.IGNORECASE)

        DATE_RANGE_REGEX = re.compile(
            r"("
            r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
            r"[a-z]*\s+\d{4}"
            r"\s*[-–]\s*"
            r"(Present|Current|"
            r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
            r"[a-z]*\s+\d{4})"
            r")",
            re.IGNORECASE
        )

        BULLET_REGEX = re.compile(r"^[•\-\*]")

        experiences = []

        for section_name, section in (parsed_document.sections.items()):

            if not EXPERIENCE_SECTION_REGEX.search(section_name):
                continue

            lines = section.lines

            current_company = None
            current_title = None
            current_duration = None
            current_description = []

            for idx, line in enumerate(lines):

                text = line.text.strip()

                if not text:
                    continue
                if (line.bold and not BULLET_REGEX.search(text) and not DATE_RANGE_REGEX.search(text)):
                    current_company = text
                    continue

                if DATE_RANGE_REGEX.search(text):

                    if (current_title or current_description):

                        experiences.append(Experience( title=(current_title or "Unknown"),
                                                      company=(current_company or "Unknown"),
                                                      duration=(current_duration or "Unknown"),
                                                      description="\n".join(current_description).strip())
                                           )

                    current_duration = text
                    current_description = []

                    if idx > 0:

                        prev_line = (lines[idx - 1].text.strip())

                        if (prev_line != current_company):
                            current_title = prev_line

                    continue
                
                current_description.append(text)

            if (current_title or current_description):

                experiences.append(Experience(title=(current_title or "Unknown"),
                                              company=(current_company or "Unknown"),
                                              duration=(current_duration or "Unknown"),
                                              description="\n".join(current_description).strip())
                                   )

        return experiences

    def __build_full_text(self,parsed_document: ParsedDocument) -> str:

        chunks = []
        for section in (parsed_document.sections.values()):
            chunks.append(section.content)
        return "\n".join(chunks)
