from pathlib import Path
from app.core.logging import AppLogger
import json

BASE_STORAGE_PATH = Path("temp_working_storage_area/session_data")
logger = AppLogger("FileStore")

class FileStore:
    def __init__(self):
        logger.info("Initializing FileStore for file-based session data management.")
        BASE_STORAGE_PATH.mkdir(parents=True,exist_ok=True)
        
    def create_session_directory(self, session_id: str, uploaded_file_id: str) -> Path:
        logger.info(f"Creating session directory for session_id: {session_id} and uploaded_file_id: {uploaded_file_id}")
        session_path = (BASE_STORAGE_PATH / session_id / uploaded_file_id)
        session_path.mkdir(parents=True, exist_ok=True)
        return session_path
    
    def save_json (self, session_id: str, uploaded_file_id: str, file_name: str, data: dict):
        logger.info(f"Saving JSON for session_id: {session_id}, uploaded_file_id: {uploaded_file_id}, file_name: {file_name}")
        session_path = self.create_session_directory(session_id, uploaded_file_id)
        json_path = session_path / file_name
        with open(json_path, "w") as f:
            json.dump(data, f, indent=4)
    
    def read_json (self, session_id: str, uploaded_file_id: str, file_name: str) -> dict:
        logger.info(f"Reading JSON for session_id: {session_id}, uploaded_file_id: {uploaded_file_id}, file_name: {file_name}")
        json_path = BASE_STORAGE_PATH / session_id / uploaded_file_id / file_name
        if not json_path.exists():
            logger.error(f"JSON file not found at path: {json_path}")
            raise FileNotFoundError(f"JSON file not found at path: {json_path}")
        with open(json_path, "r") as f:
            return json.load(f)
        
    def save_file(self, session_id: str, uploaded_file_id: str, file_name: str, file_data: bytes) -> str:
        logger.info(f"Saving file for session_id: {session_id}, uploaded_file_id: {uploaded_file_id}, file_name: {file_name}")
        session_path = self.create_session_directory(session_id, uploaded_file_id)
        file_path = session_path / file_name
        with open(file_path, "wb") as f:
            f.write(file_data)
        logger.debug(f"File saved at path: {file_path}")
        return str(file_path)
 