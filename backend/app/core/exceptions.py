"""
Exception hierarchy for the Resume Parser application.

Provides a comprehensive set of custom exceptions organized by domain (storage,
parsing, service, API) with unique error codes, HTTP status mappings, and proper
context handling.

Error codes follow the pattern: DOMAIN_NUMBER (e.g., "PARSE_001", "STORE_001")
"""

from typing import Any, Dict, Optional
from fastapi import status

class BaseResumeException(Exception):
    """
    Base exception for all resume parser exceptions.

    Provides common functionality: error codes, HTTP status mapping, detailed
    context, and clean string representation.

    Attributes:
        error_code: Unique identifier for the error (e.g., "PARSE_001")
        message: Human-readable error message
        details: Additional context about the error (dict)
        http_status_code: HTTP status code for API responses
    """

    error_code: str = "UNKNOWN_000"
    http_status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        *args: Any,
    ) -> None:
        """
        Initialize the exception.

        Args:
            message: Human-readable error message
            details: Additional context (file paths, sizes, etc.)
            *args: Additional positional arguments for Exception
        """
        self.message = message
        self.details = details or {}
        super().__init__(message, *args)

    def __str__(self) -> str:
        """Return formatted exception string."""
        base = f"[{self.error_code}] {self.message}"
        if self.details:
            details_str = ", ".join(
                f"{k}={v!r}" for k, v in self.details.items()
            )
            return f"{base} ({details_str})"
        return base

    def __repr__(self) -> str:
        """Return exception representation."""
        return f"{self.__class__.__name__}({self.message!r}, {self.details!r})"

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses."""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
        }

class StorageException(BaseResumeException):
    """Base exception for storage-related errors."""

    error_code: str = "STORE_000"
    http_status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR


class FileNotFoundError(StorageException):
    """Raised when a required file is not found in storage."""

    error_code: str = "STORE_001"
    http_status_code: int = status.HTTP_404_NOT_FOUND

    def __init__(self, file_path: str, **kwargs: Any) -> None:
        """
        Initialize FileNotFoundError.

        Args:
            file_path: Path to the missing file
            **kwargs: Additional context
        """
        message = f"File not found: {file_path}"
        details = {"file_path": file_path, **kwargs}
        super().__init__(message, details)


class SessionNotFoundError(StorageException):
    """Raised when a session is not found in storage."""

    error_code: str = "STORE_002"
    http_status_code: int = status.HTTP_404_NOT_FOUND

    def __init__(self, session_id: str, **kwargs: Any) -> None:
        """
        Initialize SessionNotFoundError.

        Args:
            session_id: ID of the missing session
            **kwargs: Additional context
        """
        message = f"Session not found: {session_id}"
        details = {"session_id": session_id, **kwargs}
        super().__init__(message, details)


class MetadataCorruptedError(StorageException):
    """Raised when stored metadata is corrupted or invalid."""

    error_code: str = "STORE_003"
    http_status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR

    def __init__(
        self, file_path: str, reason: str = "Unknown", **kwargs: Any
    ) -> None:
        """
        Initialize MetadataCorruptedError.

        Args:
            file_path: Path to the corrupted metadata file
            reason: Reason for corruption
            **kwargs: Additional context
        """
        message = f"Metadata corrupted in {file_path}: {reason}"
        details = {"file_path": file_path, "reason": reason, **kwargs}
        super().__init__(message, details)


class ParsingException(BaseResumeException):
    """Base exception for document parsing errors."""

    error_code: str = "PARSE_000"
    http_status_code: int = status.HTTP_400_BAD_REQUEST


class InvalidFileFormatError(ParsingException):
    """Raised when a file format is not supported or invalid."""

    error_code: str = "PARSE_001"
    http_status_code: int = status.HTTP_400_BAD_REQUEST

    def __init__(
        self,
        file_path: str,
        file_type: str,
        supported_types: Optional[list] = None,
        **kwargs: Any,
    ) -> None:
        """
        Initialize InvalidFileFormatError.

        Args:
            file_path: Path to the invalid file
            file_type: The invalid file type
            supported_types: List of supported file types
            **kwargs: Additional context
        """
        supported = supported_types or ["PDF", "DOCX"]
        message = (
            f"File format not supported. "
            f"Received: {file_type}, Supported: {', '.join(supported)}"
        )
        details = {
            "file_path": file_path,
            "file_type": file_type,
            "supported_types": supported,
            **kwargs,
        }
        super().__init__(message, details)


class PDFParsingError(ParsingException):
    """Raised when PDF parsing fails."""

    error_code: str = "PARSE_002"
    http_status_code: int = status.HTTP_400_BAD_REQUEST

    def __init__(
        self, file_path: str, reason: str = "Unknown", **kwargs: Any
    ) -> None:
        """
        Initialize PDFParsingError.

        Args:
            file_path: Path to the problematic PDF file
            reason: Reason for parsing failure
            **kwargs: Additional context
        """
        message = f"PDF parsing failed for {file_path}: {reason}"
        details = {"file_path": file_path, "reason": reason, **kwargs}
        super().__init__(message, details)


class TextExtractionError(ParsingException):
    """Raised when text extraction from a document fails."""

    error_code: str = "PARSE_003"
    http_status_code: int = status.HTTP_400_BAD_REQUEST

    def __init__(
        self,
        file_path: str,
        extraction_method: str = "Unknown",
        reason: str = "Unknown",
        **kwargs: Any,
    ) -> None:
        """
        Initialize TextExtractionError.

        Args:
            file_path: Path to the document
            extraction_method: Method used for extraction
            reason: Reason for extraction failure
            **kwargs: Additional context
        """
        message = (
            f"Text extraction failed for {file_path} "
            f"using {extraction_method}: {reason}"
        )
        details = {
            "file_path": file_path,
            "extraction_method": extraction_method,
            "reason": reason,
            **kwargs,
        }
        super().__init__(message, details)


class ServiceException(BaseResumeException):
    """Base exception for service-level errors."""

    error_code: str = "SRVCE_000"
    http_status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR


class ResumeParsingFailedError(ServiceException):
    """Raised when resume parsing service operation fails."""

    error_code: str = "SRVCE_001"
    http_status_code: int = status.HTTP_422_UNPROCESSABLE_ENTITY

    def __init__(
        self,
        file_path: str,
        step: str = "Unknown",
        reason: str = "Unknown",
        **kwargs: Any,
    ) -> None:
        """
        Initialize ResumeParsingFailedError.

        Args:
            file_path: Path to the resume file
            step: Processing step where failure occurred
            reason: Reason for failure
            **kwargs: Additional context
        """
        message = (
            f"Resume parsing failed at step '{step}' "
            f"for {file_path}: {reason}"
        )
        details = {
            "file_path": file_path,
            "step": step,
            "reason": reason,
            **kwargs,
        }
        super().__init__(message, details)


class ValidationFailedError(ServiceException):
    """Raised when data validation fails."""

    error_code: str = "SRVCE_002"
    http_status_code: int = status.HTTP_400_BAD_REQUEST

    def __init__(
        self,
        entity: str,
        validation_errors: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ) -> None:
        """
        Initialize ValidationFailedError.

        Args:
            entity: The entity being validated
            validation_errors: Dictionary of field -> error messages
            **kwargs: Additional context
        """
        errors_str = (
            "; ".join(f"{k}: {v}" for k, v in (validation_errors or {}).items())
            if validation_errors
            else "Unknown validation errors"
        )
        message = f"Validation failed for {entity}: {errors_str}"
        details = {
            "entity": entity,
            "validation_errors": validation_errors or {},
            **kwargs,
        }
        super().__init__(message, details)


class LLMNotConfiguredError(ServiceException):
    """Raised when an AI feature is used but no LLM provider is configured."""

    error_code: str = "SRVCE_003"
    http_status_code: int = status.HTTP_503_SERVICE_UNAVAILABLE

    def __init__(self, provider: str, **kwargs: Any) -> None:
        message = (
            f"LLM provider '{provider}' is not available. "
            "Set LLM_PROVIDER to enable AI evaluation."
        )
        super().__init__(message, {"provider": provider, **kwargs})


class EvaluationFailedError(ServiceException):
    """Raised when the LLM response cannot be parsed into a valid result."""

    error_code: str = "SRVCE_004"
    http_status_code: int = status.HTTP_502_BAD_GATEWAY

    def __init__(self, step: str, reason: str, **kwargs: Any) -> None:
        message = f"AI evaluation failed at '{step}': {reason}"
        super().__init__(message, {"step": step, "reason": reason, **kwargs})


class APIException(BaseResumeException):
    """Base exception for API-level errors."""

    error_code: str = "API_000"
    http_status_code: int = status.HTTP_400_BAD_REQUEST


class InvalidInputError(APIException):
    """Raised when API input validation fails."""

    error_code: str = "API_001"
    http_status_code: int = status.HTTP_400_BAD_REQUEST

    def __init__(
        self,
        field: str,
        reason: str = "Invalid input",
        expected: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """
        Initialize InvalidInputError.

        Args:
            field: Field with invalid input
            reason: Reason why input is invalid
            expected: Description of expected input
            **kwargs: Additional context
        """
        message = f"Invalid input for field '{field}': {reason}"
        if expected:
            message += f" (expected: {expected})"
        details = {
            "field": field,
            "reason": reason,
            "expected": expected,
            **kwargs,
        }
        super().__init__(message, details)


class NotFoundError(APIException):
    """Raised when a requested resource is not found."""

    error_code: str = "API_002"
    http_status_code: int = status.HTTP_404_NOT_FOUND

    def __init__(
        self,
        resource_type: str,
        resource_id: str,
        **kwargs: Any,
    ) -> None:
        """
        Initialize NotFoundError.

        Args:
            resource_type: Type of resource (e.g., 'Resume', 'Session')
            resource_id: ID of the missing resource
            **kwargs: Additional context
        """
        message = f"{resource_type} not found: {resource_id}"
        details = {
            "resource_type": resource_type,
            "resource_id": resource_id,
            **kwargs,
        }
        super().__init__(message, details)


class ResumeExceptions:
    """
    Backward compatibility wrapper for legacy code.

    DEPRECATED: Use specific exception classes directly instead.
    This class is maintained for backward compatibility only.
    """

    # Legacy exception alias
    FileTypeNotAllowed = InvalidFileFormatError
            