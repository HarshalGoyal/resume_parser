import logging
from typing import Any
from app.core.config import settings

class AppLogger:
    """Application logger for structured logging across backend modules."""
    
    def __init__(self, name: str) -> None:
        """Initialize AppLogger with stream and file handlers.
        
        Args:
            name: Logger name for identification in logs
        """
        self._logger: logging.Logger = logging.getLogger(name)

        if not self._logger.handlers:
            self._logger.setLevel(getattr(logging, settings.log_level))

            handler = logging.StreamHandler()
            file_handler = logging.FileHandler('backend_app.log')
            formatter = logging.Formatter(
                '[%(asctime)s] [%(levelname)s] %(name)s: %(message)s'
            )

            handler.setFormatter(formatter)
            file_handler.setFormatter(formatter)
            self._logger.addHandler(handler)
            self._logger.addHandler(file_handler)


    def info(self, message: str) -> None:
        """Log info level message.
        
        Args:
            message: Message to log
        """
        self._logger.info(message)

    def debug(self, message: str) -> None:
        """Log debug level message.
        
        Args:
            message: Message to log
        """
        self._logger.debug(message)

    def error(self, message: str) -> None:
        """Log error level message.
        
        Args:
            message: Message to log
        """
        self._logger.error(message)

        
