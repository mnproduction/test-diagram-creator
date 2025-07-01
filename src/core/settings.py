"""
Centralized Settings Management for AI Diagram Creator
"""

from typing import Any

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings

# Note: We still load dotenv for compatibility, but BaseSettings can handle .env files directly


class GeminiSettings(BaseModel):
    """Google Gemini LLM configuration"""

    api_key: str | None = Field(
        default=None,
        description="Google Gemini API key",
    )
    model_name: str = Field(
        default="google-gla:gemini-2.0-flash",
        description="Gemini model name to use (format: google-gla:model-name)",
    )
    requests_per_minute: int = Field(
        default=10,
        ge=1,
        le=1000,
        description="Maximum requests per minute for Gemini API",
    )
    timeout_seconds: int = Field(
        default=30,
        ge=5,
        le=300,
        description="Request timeout in seconds",
    )
    rate_limit_delay: float = Field(
        default=6.0,
        ge=0.1,
        le=60.0,
        description="Delay between requests to respect rate limits (seconds)",
    )

    @field_validator("model_name")
    def validate_model_name(cls, v):
        if not v:
            raise ValueError("Model name cannot be empty")
        return v


class ServerSettings(BaseModel):
    """Server configuration"""

    host: str = Field(
        default="0.0.0.0",
        description="Server host address",
    )
    port: int = Field(
        default=8000,
        ge=1,
        le=65535,
        description="Server port",
    )
    debug: bool = Field(
        default=False,
        description="Enable debug mode",
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level",
    )

    @field_validator("log_level")
    def validate_log_level(cls, v):
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        return v.upper()


class SecuritySettings(BaseModel):
    """Security and CORS configuration"""

    api_key: str = Field(
        default="dev-key",
        description="A master API key for development or single-key setups.",
    )
    allowed_api_keys: list[str] = Field(
        default=["dev-key-1", "dev-key-2"],
        description="A list of allowed API keys for production environments.",
    )
    cors_origins: list[str] = Field(
        default=["*"],
        description="CORS allowed origins",
    )
    cors_credentials: bool = Field(
        default=True,
        description="Enable CORS credentials",
    )
    max_requests_per_minute: int = Field(
        default=10,
        ge=1,
        le=1000,
        description="Maximum requests per minute per client",
    )


class DiagramSettings(BaseModel):
    """Diagram generation configuration"""

    default_output_format: str = Field(
        default="png",
        description="Default output format for diagrams",
    )
    max_nodes_per_diagram: int = Field(
        default=50,
        ge=1,
        le=200,
        description="Maximum nodes per diagram",
    )
    max_diagram_size_mb: int = Field(
        default=5,
        ge=1,
        le=100,
        description="Maximum diagram size in MB",
    )
    generation_timeout: int = Field(
        default=30,
        ge=5,
        le=300,
        description="Diagram generation timeout in seconds",
    )
    temp_file_timeout: int = Field(
        default=300,
        ge=60,
        le=3600,
        description="Temporary file cleanup timeout in seconds",
    )

    @field_validator("default_output_format")
    def validate_output_format(cls, v):
        valid_formats = ["png", "svg", "pdf"]
        if v.lower() not in valid_formats:
            raise ValueError(f"Output format must be one of {valid_formats}")
        return v.lower()


class FeatureSettings(BaseModel):
    """Feature toggles and optional functionality"""

    enable_assistant_mode: bool = Field(
        default=False,
        description="Enable assistant chat mode",
    )
    enable_llm_mocking: bool = Field(
        default=False,
        description="Enable LLM mocking for development/testing",
    )
    dev_mode: bool = Field(
        default=False,
        description="Enable development features",
    )
    verbose_logging: bool = Field(
        default=False,
        description="Enable verbose logging",
    )


class LoggingSettings(BaseModel):
    """Logging and monitoring configuration"""

    logfire_token: str | None = Field(
        default=None,
        description="Logfire token for centralized logging",
    )
    enable_logfire: bool = Field(
        default=False,
        description="Enable Logfire logging",
    )


class Settings(BaseSettings):
    """Main settings class combining all configuration sections"""

    gemini_api_key: str | None = Field(default=None, alias="GEMINI_API_KEY")
    gemini_model: str = Field(
        default="google-gla:gemini-2.0-flash", alias="GEMINI_MODEL"
    )
    gemini_rpm: int = Field(default=10, alias="GEMINI_RPM")
    gemini_timeout: int = Field(default=30, alias="GEMINI_TIMEOUT")
    gemini_rate_limit_delay: float = Field(default=6.0, alias="GEMINI_RATE_LIMIT_DELAY")

    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")
    debug: bool = Field(default=False, alias="DEBUG")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    cors_origins: str = Field(default="*", alias="CORS_ORIGINS")
    cors_credentials: bool = Field(default=True, alias="CORS_CREDENTIALS")
    max_requests_per_minute: int = Field(default=10, alias="MAX_REQUESTS_PER_MINUTE")

    default_output_format: str = Field(default="png", alias="DEFAULT_OUTPUT_FORMAT")
    max_nodes_per_diagram: int = Field(default=50, alias="MAX_NODES_PER_DIAGRAM")
    max_diagram_size_mb: int = Field(default=5, alias="MAX_DIAGRAM_SIZE_MB")
    diagram_timeout: int = Field(default=30, alias="DIAGRAM_TIMEOUT")
    temp_file_timeout: int = Field(default=300, alias="TEMP_FILE_TIMEOUT")

    enable_assistant: bool = Field(default=False, alias="ENABLE_ASSISTANT")
    mock_llm: bool = Field(default=False, alias="MOCK_LLM")
    dev_mode: bool = Field(default=False, alias="DEV_MODE")
    verbose_logging: bool = Field(default=False, alias="VERBOSE_LOGGING")

    logfire_token: str | None = Field(default=None, alias="LOGFIRE_TOKEN")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
    }

    # Computed properties for backward compatibility
    @property
    def gemini(self) -> GeminiSettings:
        """Get Gemini settings"""
        return GeminiSettings(
            api_key=self.gemini_api_key,
            model_name=self.gemini_model,
            requests_per_minute=self.gemini_rpm,
            timeout_seconds=self.gemini_timeout,
            rate_limit_delay=self.gemini_rate_limit_delay,
        )

    @property
    def server(self) -> ServerSettings:
        """Get server settings"""
        return ServerSettings(
            host=self.host,
            port=self.port,
            debug=self.debug,
            log_level=self.log_level,
        )

    @property
    def security(self) -> SecuritySettings:
        """Get security settings"""
        return SecuritySettings(
            cors_origins=self.cors_origins.split(",")
            if self.cors_origins != "*"
            else ["*"],
            cors_credentials=self.cors_credentials,
            max_requests_per_minute=self.max_requests_per_minute,
        )

    @property
    def diagram(self) -> DiagramSettings:
        """Get diagram settings"""
        return DiagramSettings(
            default_output_format=self.default_output_format,
            max_nodes_per_diagram=self.max_nodes_per_diagram,
            max_diagram_size_mb=self.max_diagram_size_mb,
            generation_timeout=self.diagram_timeout,
            temp_file_timeout=self.temp_file_timeout,
        )

    @property
    def features(self) -> FeatureSettings:
        """Get feature settings"""
        return FeatureSettings(
            enable_assistant_mode=self.enable_assistant,
            enable_llm_mocking=self.mock_llm,
            dev_mode=self.dev_mode,
            verbose_logging=self.verbose_logging,
        )

    @property
    def logging(self) -> LoggingSettings:
        """Get logging settings"""
        return LoggingSettings(
            logfire_token=self.logfire_token,
            enable_logfire=bool(self.logfire_token),
        )

    def get_rate_limit_delay(self) -> float:
        """Calculate rate limit delay based on RPM setting"""
        return 60.0 / self.gemini_rpm

    def is_production(self) -> bool:
        """Check if running in production mode"""
        return not self.debug and not self.dev_mode

    def get_cors_config(self) -> dict[str, Any]:
        """Get CORS configuration for FastAPI"""
        origins = self.cors_origins.split(",") if self.cors_origins != "*" else ["*"]
        return {
            "allow_origins": origins,
            "allow_credentials": self.cors_credentials,
            "allow_methods": ["*"],
            "allow_headers": ["*"],
        }

    def validate_required_settings(self) -> list[str]:
        """Validate that all required settings are present"""
        errors = []
        if not self.gemini_api_key and not self.mock_llm:
            errors.append("GEMINI_API_KEY is required when LLM mocking is disabled")
        return errors


# Global settings instance
settings = Settings()

# Convenience exports for backward compatibility
gemini_settings = settings.gemini
server_settings = settings.server
security_settings = settings.security
diagram_settings = settings.diagram
feature_settings = settings.features
logging_settings = settings.logging
