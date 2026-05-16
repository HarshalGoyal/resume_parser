from pathlib import Path
from typing import Any
from app.core.logging import AppLogger
import json
from app.core.config import settings


BASE_STORAGE_PATH: Path = Path(settings.storage_path)
logger = AppLogger("FileStore")

class FileStore:
    """File-based storage for session data persistence."""
    
    def __init__(self) -> None:
        """Initialize FileStore and create base storage directory."""
        logger.info("Initializing FileStore for file-based session data management.")
        BASE_STORAGE_PATH.mkdir(parents=True, exist_ok=True)
        
    def create_session_directory(self, session_id: str, uploaded_file_id: str) -> Path:
        """Create a session-specific directory for storing upload data.
        
        Args:
            session_id: Unique session identifier
            uploaded_file_id: Unique upload identifier within the session
            
        Returns:
            Path object pointing to the created directory
        """
        logger.info(f"Creating session directory for session_id: {session_id} and uploaded_file_id: {uploaded_file_id}")
        session_path: Path = BASE_STORAGE_PATH / session_id / uploaded_file_id
        session_path.mkdir(parents=True, exist_ok=True)
        return session_path
    
    def save_json(self, session_id: str, uploaded_file_id: str, file_name: str, data: dict[str, Any]) -> None:
        """Save JSON data to a file within a session directory.
        
        Args:
            session_id: Unique session identifier
            uploaded_file_id: Unique upload identifier within the session
            file_name: Name of the JSON file to save
            data: Dictionary data to serialize and save
        """
        logger.info(f"Saving JSON for session_id: {session_id}, uploaded_file_id: {uploaded_file_id}, file_name: {file_name}")
        session_path: Path = self.create_session_directory(session_id, uploaded_file_id)
        json_path: Path = session_path / file_name
        with open(json_path, "w") as f:
            json.dump(data, f, indent=4)
    
    def read_json(self, session_id: str, uploaded_file_id: str, file_name: str) -> dict[str, Any]:
        """Read JSON data from a file within a session directory.
        
        Args:
            session_id: Unique session identifier
            uploaded_file_id: Unique upload identifier within the session
            file_name: Name of the JSON file to read
            
        Returns:
            Deserialized dictionary from JSON file
            
        Raises:
            FileNotFoundError: If the JSON file doesn't exist
        """
        logger.info(f"Reading JSON for session_id: {session_id}, uploaded_file_id: {uploaded_file_id}, file_name: {file_name}")
        json_path: Path = BASE_STORAGE_PATH / session_id / uploaded_file_id / file_name
        if not json_path.exists():
            logger.error(f"JSON file not found at path: {json_path}")
            raise FileNotFoundError(f"JSON file not found at path: {json_path}")
        with open(json_path, "r") as f:
            return json.load(f)
        
    def save_file(self, session_id: str, uploaded_file_id: str, file_name: str, file_data: bytes) -> str:
        """Save binary file data within a session directory.
        
        Args:
            session_id: Unique session identifier
            uploaded_file_id: Unique upload identifier within the session
            file_name: Name of the file to save
            file_data: Binary file content
            
        Returns:
            String path where the file was saved
        """
        logger.info(f"Saving file for session_id: {session_id}, uploaded_file_id: {uploaded_file_id}, file_name: {file_name}")
        session_path: Path = self.create_session_directory(session_id, uploaded_file_id)
        file_path: Path = session_path / file_name
        with open(file_path, "wb") as f:
            f.write(file_data)
        logger.debug(f"File saved at path: {file_path}")
        return str(file_path)
 