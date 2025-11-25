"""
Configuration module for the application. This module loads settings from environment variables
and provides structured access to database, LLM provider, and server configurations.
"""

import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


@dataclass
class DatabaseConfig:
    """MongoDB database configuration"""

    url: str
    name: str

    @classmethod
    def from_env(cls) -> "DatabaseConfig":
        """Load database configuration from environment variables"""
        url = os.getenv("DATABASE_URL")
        name = os.getenv("DATABASE_NAME", "ADA")

        if not url:
            raise ValueError("DATABASE_URL environment variable is required")

        return cls(url=url, name=name)


@dataclass
class LLMConfig:
    """LLM provider configuration"""

    openai_key: Optional[str] = None
    anthropic_key: Optional[str] = None
    google_key: Optional[str] = None
    github_token: Optional[str] = None
    default_provider: str = "openai"

    @classmethod
    def from_env(cls) -> "LLMConfig":
        """Load LLM configuration from environment variables"""
        config = cls(
            openai_key=os.getenv("OPENAI_API_KEY"),
            anthropic_key=os.getenv("ANTHROPIC_API_KEY"),
            google_key=os.getenv("GOOGLE_API_KEY"),
            github_token=os.getenv("GITHUB_API_TOKEN"),
        )

        if config.google_key:
            config.default_provider = "google"
        elif config.openai_key:
            config.default_provider = "openai"
        elif config.github_token:
            config.default_provider = "github"
        elif config.anthropic_key:
            config.default_provider = "anthropic"

        return config

    def get_api_key(self, provider: str) -> str | None:
        """Get API key for specific provider"""
        key_map = {
            "openai": self.openai_key,
            "anthropic": self.anthropic_key,
            "google": self.google_key,
            "github": self.github_token,
        }
        return key_map.get(provider.lower())

    def has_any_key(self) -> bool:
        """Check if at least one LLM API key is configured"""
        return bool(
            self.openai_key
            or self.anthropic_key
            or self.google_key
            or self.github_token
        )


@dataclass
class ServerConfig:
    """Server configuration"""

    host: str
    port: int
    debug: bool

    @classmethod
    def from_env(cls) -> "ServerConfig":
        """Load server configuration from environment variables"""
        return cls(
            host=os.getenv("HOST", "0.0.0.0"),
            port=int(os.getenv("PORT", "8000")),
            debug=os.getenv("DEBUG", "False").lower() == "true",
        )


@dataclass
class AppConfig:
    """Application-wide configuration"""

    database: DatabaseConfig
    llm: LLMConfig
    server: ServerConfig

    @classmethod
    def load(cls) -> "AppConfig":
        """Load all configuration from environment"""
        return cls(
            database=DatabaseConfig.from_env(),
            llm=LLMConfig.from_env(),
            server=ServerConfig.from_env(),
        )
