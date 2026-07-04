from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application configuration settings with environment variable support.
    
    Configuration is loaded from environment variables and .env files.
    Environment variables take precedence over .env file values.
    """

    app_name: str = Field(
        default="Resume Parser API",
        description="Name of the application"
    )
    version: str = Field(
        default="1.0.0",
        description="Application version"
    )
    debug: bool = Field(
        default=False,
        description="Enable debug mode",
        alias="DEBUG"
    )
    allowed_hosts: List[str] = Field(
        default=["localhost", "127.0.0.1"],
        description="List of allowed hosts for CORS",
        alias="ALLOWED_HOSTS"
    )
    upload_max_size: int = Field(
        default=50 * 1024 * 1024,
        description="Maximum upload file size in bytes (default: 50MB)",
        alias="UPLOAD_MAX_SIZE"
    )
    session_timeout_minutes: int = Field(
        default=3600,
        description="Session timeout in minutes (default: 3600 minutes = 60 hours)",
        alias="SESSION_TIMEOUT_MINUTES"
    )
    storage_path: str = Field(
        default="temp_working_storage_area/session_data",
        description="Path for storing uploaded files and session data",
        alias="STORAGE_PATH"
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
        alias="LOG_LEVEL"
    )
    log_file: str = Field(
        default="backend_app.log",
        description="Path to the rotating application log file",
        alias="LOG_FILE"
    )
    llm_provider: str = Field(
        default="",
        description="LLM provider for AI evaluation ('' = disabled; 'fake' for tests)",
        alias="LLM_PROVIDER"
    )
    llm_model: str = Field(
        default="",
        description="Model identifier passed to the LLM provider",
        alias="LLM_MODEL"
    )
    llm_api_key: str = Field(
        default="",
        description="Generic API key override for the active LLM provider (never logged)",
        alias="LLM_API_KEY"
    )
    anthropic_api_key: str = Field(
        default="",
        description="API key used when the Anthropic provider is active",
        alias="ANTHROPIC_API_KEY"
    )
    openai_api_key: str = Field(
        default="",
        description="API key used when the OpenAI provider is active",
        alias="OPENAI_API_KEY"
    )
    google_api_key: str = Field(
        default="",
        description="API key used when the Google/Gemini provider is active",
        alias="GOOGLE_API_KEY"
    )
    llm_fake_response: str = Field(
        default="{}",
        description="Canned response used by the 'fake' provider (tests/dev only)",
        alias="LLM_FAKE_RESPONSE"
    )

    class Config:
        """Pydantic configuration for Settings."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        populate_by_name = True

    @field_validator("debug", mode="before")
    @classmethod
    def parse_bool(cls, v):
        """Convert string representations of boolean to actual boolean."""
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.lower() in ("true", "1", "yes", "on")
        return bool(v)

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v):
        """Validate log level is one of the accepted values."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper_v = v.upper()
        if upper_v not in valid_levels:
            raise ValueError(
                f"log_level must be one of {valid_levels}, got: {v}"
            )
        return upper_v

    @field_validator("upload_max_size")
    @classmethod
    def validate_upload_size(cls, v):
        """Ensure upload max size is positive."""
        if v <= 0:
            raise ValueError("upload_max_size must be greater than 0")
        return v

    @field_validator("session_timeout_minutes")
    @classmethod
    def validate_timeout(cls, v):
        """Ensure session timeout is positive."""
        if v <= 0:
            raise ValueError("session_timeout_minutes must be greater than 0")
        return v


settings = Settings()