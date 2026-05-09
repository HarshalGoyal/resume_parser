from fastapi import HTTPException, status   #type: ignore
from ...core.logging import AppLogger       #type: ignore

class ResumeExceptions:
    
    def __init__(self):
        self.loggr = AppLogger("ResumeParsingExceptions")
        self.loggr.info("Initialized ResumeExceptions class for handling exceptions related to resume parsing.")

    class FileTypeNotAllowed(HTTPException):
        def __init__(self, file_path : str, file_type: str):
            self.file_path = file_path
            self.file_type = file_type
            self.message = f"File type not supported. Only PDF and DOCX are supported."
            
            self.loggr.error(self.message + f" Received file type: {file_type} for file: {file_path}")
            self.loggr.info(f"Returning 400 for {file_path} and file type: {file_type}")
            
            super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=self.message)
            