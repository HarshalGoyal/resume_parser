from pydantic import BaseModel

class Skill (BaseModel):
    
    name : str
    confidence_score : float = 1.0
    