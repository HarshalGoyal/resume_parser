from pydantic import BaseModel
from app.core.logging import AppLogger

Logger = AppLogger("DocumentLineModel")
Logger.info("Initialized DocumentLine model for representing individual lines in a document.")

class DocumentLine(BaseModel):
    
    text : str
    font_size : float = 12.0
    bold : bool = False
    fonts : list[str] = []
    bbox : list[float] = []
    page : int = 0
    links : list[str] = []
    is_header : bool = False
    
    
    
    