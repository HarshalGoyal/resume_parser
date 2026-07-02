import logging
from logging.handlers import RotatingFileHandler
from app.core.config import settings

class AppLogger:
    """Application logger for structured logging across backend modules."""

    def __init__(self, name: str) -> None:
        """Initialize AppLogger with stream and rotating file handlers.

        Args:
            name: Logger name for identification in logs
        """
        self._logger: logging.Logger = logging.getLogger(name)

        if not self._logger.handlers:
            self._logger.setLevel(getattr(logging, settings.log_level))

            handler = logging.StreamHandler()
            # Rotate to bound disk usage (5 x 10 MB) instead of growing forever.
            file_handler = RotatingFileHandler(
                settings.log_file, maxBytes=10 * 1024 * 1024, backupCount=5
            )
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

    def warning(self, message: str) -> None:
        """Log warning level message.

        Args:
            message: Message to log
        """
        self._logger.warning(message)

    def error(self, message: str) -> None:
        """Log error level message.

        Args:
            message: Message to log
        """
        self._logger.error(message)

    def exception(self, message: str) -> None:
        """Log an error-level message together with the active exception's
        traceback. Call only from within an ``except`` block.

        Args:
            message: Message to log
        """
        self._logger.exception(message)

        
