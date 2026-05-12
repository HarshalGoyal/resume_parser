from app.core.logging import AppLogger

logger = AppLogger("MemoryStore")

class MemoryStore:
    
    def __init__(self):
        logger.info("Initialized MemoryStore for in-memory session data management.")
        self.__store = {}
        
    def set(self, key : str, value: dict):
        logger.info(f"Setting value in MemoryStore for key: {key}")
        self.__store[key] = value

    def get(self, key: str) -> dict:
        logger.info(f"Getting value from MemoryStore for key: {key}")
        return self.__store.get(key)
    
    def delete(self, key: str):
        logger.info(f"Deleting value from MemoryStore for key: {key}")
        if key in self.__store:
            del self.__store[key]
    
    def exists(self, key: str) -> bool:
        logger.info(f"Checking existence of key: {key} in MemoryStore")
        return key in self.__store