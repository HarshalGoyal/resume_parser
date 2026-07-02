from pydantic import BaseModel
from app.core.logging import AppLogger

Logger = AppLogger("ContactInfoModel")
Logger.info("Initialized ContactInfo model for representing contact information in a document.")

class ContactInfo(BaseModel):
    
    emails : list[str]
    phone_numbers : list[str]
    linkedin_profiles : list[str]
    github_profiles : list[str]
    other_links : list[str]
    

