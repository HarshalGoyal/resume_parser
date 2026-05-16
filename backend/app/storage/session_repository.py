from datetime import datetime
import uuid

from app.core.logging import AppLogger
from app.models.resume_processing_stages import ResumeProcessingStages
from app.storage.memory_store import MemoryStore
from app.storage.file_store import FileStore


logger = AppLogger("SessionRepository")

class SessionRepository:

    def __init__(self):

        logger.info(
            "Initializing SessionRepository")

        self.memory_store = MemoryStore()

        self.file_store = FileStore()

    async def create_session(self) -> str:

        session_id = str(uuid.uuid4())

        logger.info(f"Created new session_id={session_id}")

        return session_id


    async def create_upload(self,session_id: str,file_name: str, file_data: bytes) -> dict:

            upload_id = str(uuid.uuid4())

            logger.info(f"Creating upload_id={upload_id} for session_id={session_id}")

            saved_file_path = self.file_store.save_file(session_id=session_id,uploaded_file_id=upload_id,
                                                            file_name=file_name,file_data=file_data)
            logger.info (f"got file: {file_name} ")
            metadata = {

                "session_id": session_id,

                "upload_id": upload_id,

                "file_name": file_name,

                "saved_file_path": saved_file_path,

                "status": ResumeProcessingStages.UPLOADED.value,

                "current_stage": ResumeProcessingStages.UPLOADED.value,

                "retry_count": 0,

                "created_at": datetime.now().isoformat(),

                "updated_at": datetime.now().isoformat(),

                "parsed_text_path": None,

                "evaluation_path": None,

                "error_message": None
            }

            self.file_store.save_json( session_id=session_id,uploaded_file_id=upload_id,
                                      file_name="metadata.json",data=metadata)

            cache_key = session_id
        
            session_cache = self.memory_store.get(cache_key) or {}
            session_cache[upload_id] = metadata
            self.memory_store.set(cache_key, session_cache)

            logger.info(f"Upload created successfully upload_id={upload_id}")

            return metadata


    async def get_upload(self,session_id: str,upload_id: str) -> dict | None:

            cache_key = session_id

            session_cache = self.memory_store.get(cache_key)

            if session_cache and upload_id in session_cache:
                logger.info(f"Cache hit for upload_id={upload_id}")
                return session_cache[upload_id]

            logger.info(f"Cache miss for upload_id={upload_id}")
        
            metadata = self.file_store.read_json(session_id=session_id, uploaded_file_id=upload_id, file_name="metadata.json")

            if metadata is None:
                logger.error(f"Upload metadata not found for upload_id={upload_id}")
                return None

            # Update the session cache with the new metadata
            session_cache = session_cache or {}
            session_cache[upload_id] = metadata
            self.memory_store.set(cache_key, session_cache)

            return metadata


    async def update_stage(self,session_id: str,upload_id: str,stage: ResumeProcessingStages) -> dict | None:

        metadata = await self.get_upload(session_id,upload_id)

        if metadata is None:
            return None

        metadata["status"] = stage.value

        metadata["current_stage"] = stage.value
        

        metadata["updated_at"] = datetime.now().isoformat()

        self.__persist_metadata(session_id,upload_id,metadata
        )

        logger.info(f"Updated stage to={stage.value} for upload_id={upload_id}")

        return metadata


    async def mark_failed(self,session_id: str,upload_id: str,error_message: str) -> dict | None:

        metadata = await self.get_upload(session_id,upload_id)

        if metadata is None:
            return None

        metadata["status"] = (ResumeProcessingStages.FAILED.value)

        metadata["current_stage"] = (ResumeProcessingStages.FAILED.value)

        metadata["error_message"] = (error_message)

        metadata["retry_count"] += 1

        metadata["updated_at"] = (datetime.now().isoformat())

        self.__persist_metadata(session_id,upload_id,metadata)

        logger.error(f"Marked upload as failed upload_id={upload_id}")

        return metadata


    def __persist_metadata(self,session_id: str,upload_id: str,metadata: dict):

            self.file_store.save_json(session_id=session_id, uploaded_file_id=upload_id,
                                      file_name="metadata.json", data=metadata)
            cache_key = session_id
        
            session_cache = self.memory_store.get(cache_key) or {}
            session_cache[upload_id] = metadata
            self.memory_store.set(cache_key, session_cache)

    def __build_cache_key(self,session_id: str,upload_id: str) -> str:
        return (f"{session_id}:{upload_id}")
