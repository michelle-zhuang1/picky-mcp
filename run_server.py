#!/usr/bin/env python3
"""Startup script for the Restaurant Recommendation MCP Server."""

import sys
import os
import argparse
import logging
from pathlib import Path

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.server import main
from src.config import validate_configuration

def setup_logging(debug: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('picky_mcp.log')
        ]
    )

def check_environment():
    """Check if environment is properly configured."""
    print("🔍 Checking environment configuration...")
    
    # Check if .env file exists
    env_file = Path('.env')
    if not env_file.exists():
        print("⚠️  .env file not found. Please create one based on .env.example")
        return False
    
    # Validate configuration
    config_status = validate_configuration()
    
    if not config_status["valid"]:
        print(f"❌ Configuration error: {config_status['message']}")
        return False
    
    print("✅ Environment configuration valid")
    
    # Check individual services
    settings = config_status["settings"]
    if settings["notion_configured"]:
        print("✅ Notion API configured")
    else:
        print("⚠️  Notion API not configured")
    
    if settings["google_maps_configured"]:
        print("✅ Google Maps API configured")
    else:
        print("⚠️  Google Maps API not configured")
    
    return True

def main_cli():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Restaurant Recommendation MCP Server")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--check-env", action="store_true", help="Check environment configuration")
    parser.add_argument("--no-sync", action="store_true", help="Disable automatic synchronization")
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.debug)
    
    # Check environment if requested
    if args.check_env:
        if check_environment():
            print("✅ Environment check passed")
            return 0
        else:
            print("❌ Environment check failed")
            return 1
    
    # Check environment before starting server
    if not check_environment():
        print("❌ Environment check failed. Please fix configuration before starting server.")
        return 1
    
    print("🚀 Starting Restaurant Recommendation MCP Server...")
    
    try:
        main()
        return 0
    except KeyboardInterrupt:
        print("\\n🛑 Server stopped by user")
        return 0
    except Exception as e:
        print(f"❌ Server error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main_cli())