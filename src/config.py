"""Configuration management for the Picky MCP Server."""

import os
from typing import Optional
from pydantic import BaseSettings, Field
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Notion API Configuration
    notion_api_key: str = Field(..., env="NOTION_API_KEY")
    notion_database_id: str = Field(..., env="NOTION_DATABASE_ID")
    
    # Google Maps API Configuration
    google_maps_api_key: str = Field(..., env="GOOGLE_MAPS_API_KEY")
    
    # MCP Server Configuration
    mcp_server_host: str = Field(default="localhost", env="MCP_SERVER_HOST")
    mcp_server_port: int = Field(default=8000, env="MCP_SERVER_PORT")
    debug: bool = Field(default=False, env="DEBUG")
    
    # Application Configuration
    max_recommendations: int = Field(default=10, env="MAX_RECOMMENDATIONS")
    default_search_radius_km: float = Field(default=25.0, env="DEFAULT_SEARCH_RADIUS_KM")
    cache_ttl_seconds: int = Field(default=3600, env="CACHE_TTL_SECONDS")
    
    class Config:
        env_file = ".env"
        case_sensitive = False


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
                "google_maps_configured": bool(settings.google_maps_api_key),
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