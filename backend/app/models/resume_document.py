from pydantic import BaseModel

from app.models.parsed_document import ParsedDocument
from app.models.contact_info import ContactInfo
from app.models.skill import Skill
from app.models.experience import Experience


class ResumeDocument (BaseModel):
    
    contact_info    : ContactInfo
    skills          : list[Skill]
    work_ex         : list[Experience]
    