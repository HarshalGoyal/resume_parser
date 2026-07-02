from typing import TypeVar, Generic

from app.core.logging import AppLogger

logger = AppLogger("MemoryStore")

T = TypeVar('T')

class MemoryStore(Generic[T]):
    """Generic in-memory store for session data caching.
    
    Type Parameters:
        T: Type of values stored in the memory store
    """
    
    def __init__(self) -> None:
        """Initialize the memory store with an empty dict."""
        logger.info("Initialized MemoryStore for in-memory session data management.")
        self.__store: dict[str, T] = {}
        
    def set(self, key: str, value: T) -> None:
        """Store a value in memory with the given key.
        
        Args:
            key: Unique identifier for the value
            value: Value to store
        """
        logger.info(f"Setting value in MemoryStore for key: {key}")
        self.__store[key] = value

    def get(self, key: str) -> T | None:
        """Retrieve a value from memory by key.
        
        Args:
            key: Identifier of the value to retrieve
            
        Returns:
            The stored value or None if key doesn't exist
        """
        logger.info(f"Getting value from MemoryStore for key: {key}")
        return self.__store.get(key)
    
    def delete(self, key: str) -> None:
        """Remove a value from memory by key.
        
        Args:
            key: Identifier of the value to delete
        """
        logger.info(f"Deleting value from MemoryStore for key: {key}")
        if key in self.__store:
            del self.__store[key]
    
    def exists(self, key: str) -> bool:
        """Check if a key exists in the store.
        
        Args:
            key: Identifier to check
            
        Returns:
            True if key exists, False otherwise
        """
        logger.info(f"Checking existence of key: {key} in MemoryStore")
        return key in self.__store