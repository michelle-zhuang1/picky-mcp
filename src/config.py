"""Configuration management for the Picky MCP Server."""

import os
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables from .env file
import pathlib
project_root = pathlib.Path(__file__).parent.parent
load_dotenv(project_root / ".env")


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Notion API Configuration
    notion_api_key: str = Field(..., env="NOTION_API_KEY")
    notion_database_id: str = Field(..., env="NOTION_DATABASE_ID")
    
    # Google Maps API Configuration  
    google_places_api_key: str = Field(..., env="GOOGLE_PLACES_API_KEY")
    
    # MCP Server Configuration
    mcp_server_host: str = Field(default="localhost", env="MCP_SERVER_HOST")
    mcp_server_port: int = Field(default=8000, env="MCP_SERVER_PORT")
    debug: bool = Field(default=False, env="DEBUG")
    
    # Application Configuration
    max_recommendations: int = Field(default=10, env="MAX_RECOMMENDATIONS")
    default_search_radius_km: float = Field(default=25.0, env="DEFAULT_SEARCH_RADIUS_KM")
    cache_ttl_seconds: int = Field(default=3600, env="CACHE_TTL_SECONDS")
    
    model_config = {"env_file": str(project_root / ".env"), "case_sensitive": False, "extra": "ignore"}


def get_settings() -> Settings:
    """Get application settings."""
    return Settings()


def validate_configuration() -> dict:
    """Validate that all required configuration is present."""
    try:
        settings = get_settings()
        return {
            "valid": True,
            "message": "Configuration valid",
            "settings": {
                "notion_configured": bool(settings.notion_api_key and settings.notion_database_id),
                "google_maps_configured": bool(settings.google_places_api_key),
                "debug_mode": settings.debug,
            }
        }
    except Exception as e:
        return {
            "valid": False,
            "message": f"Configuration error: {str(e)}",
            "settings": {}
        }


# Global settings instance
settings = get_settings()