#!/usr/bin/env python3
"""Setup script for Restaurant Recommendation MCP Server."""

import os
import sys
import json
from pathlib import Path

def create_env_file():
    """Create .env file from template."""
    env_example = Path('.env.example')
    env_file = Path('.env')
    
    if env_file.exists():
        response = input("📝 .env file already exists. Overwrite? (y/N): ")
        if response.lower() != 'y':
            print("Skipping .env file creation")
            return
    
    print("🔧 Creating .env file...")
    
    # Get API keys from user
    print("\\n📋 Please provide your API keys:")
    
    notion_api_key = input("🔗 Notion API Key: ").strip()
    notion_database_id = input("🗄️  Notion Database ID: ").strip()
    google_maps_api_key = input("🗺️  Google Maps API Key: ").strip()
    
    # Create .env file
    env_content = f"""# Notion API Configuration
NOTION_API_KEY={notion_api_key}
NOTION_DATABASE_ID={notion_database_id}

# Google Maps API Configuration
GOOGLE_MAPS_API_KEY={google_maps_api_key}

# MCP Server Configuration
MCP_SERVER_HOST=localhost
MCP_SERVER_PORT=8000
DEBUG=false

# Application Configuration
MAX_RECOMMENDATIONS=10
DEFAULT_SEARCH_RADIUS_KM=25.0
CACHE_TTL_SECONDS=3600
"""
    
    with open(env_file, 'w') as f:
        f.write(env_content)
    
    print(f"✅ Created .env file with your configuration")

def install_dependencies():
    """Install required dependencies."""
    print("📦 Installing dependencies...")
    
    try:
        import subprocess
        result = subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Dependencies installed successfully")
        else:
            print(f"❌ Failed to install dependencies: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error installing dependencies: {e}")
        return False
    
    return True

def display_notion_setup_instructions():
    """Display Notion setup instructions."""
    print("""
🔧 NOTION SETUP INSTRUCTIONS:

1. Create a new Notion integration:
   • Go to https://www.notion.so/my-integrations
   • Click "New integration"
   • Give it a name like "Restaurant MCP Server"
   • Select the workspace
   • Click "Submit"

2. Copy the integration token:
   • Copy the "Internal Integration Token"
   • This is your NOTION_API_KEY

3. Create a restaurant database:
   • Create a new page in Notion
   • Add a database (Table view)
   • Add the following properties:
     - Name (Title)
     - Rating (Number)
     - Cuisine (Multi-select)
     - Location (Text)
     - City (Text)
     - State (Text)
     - Date Visited (Date)
     - Notes (Text)
     - Google Place ID (Text)
     - Price Range (Select with options: $, $$, $$$, $$$$)
     - Vibes (Multi-select)
     - Revisit (Checkbox)
     - Wishlist (Checkbox)

4. Share the database with your integration:
   • Click "Share" on your database page
   • Invite your integration by name
   • Give it "Edit" permissions

5. Copy the database ID:
   • From the database URL: https://notion.so/your-database-id
   • This is your NOTION_DATABASE_ID
""")

def display_google_maps_setup_instructions():
    """Display Google Maps setup instructions."""
    print("""
🗺️ GOOGLE MAPS SETUP INSTRUCTIONS:

1. Go to Google Cloud Console:
   • Visit https://console.cloud.google.com/

2. Create or select a project:
   • Create a new project or select an existing one

3. Enable the Places API:
   • Go to "APIs & Services" > "Library"
   • Search for "Places API"
   • Click "Enable"

4. Create an API key:
   • Go to "APIs & Services" > "Credentials"
   • Click "Create Credentials" > "API Key"
   • Copy the API key

5. Restrict the API key (recommended):
   • Click on the API key to edit
   • Under "Application restrictions", select "HTTP referrers"
   • Under "API restrictions", select "Restrict key"
   • Choose "Places API"
   • Save the changes

6. Copy the API key:
   • This is your GOOGLE_MAPS_API_KEY
""")

def test_configuration():
    """Test the configuration."""
    print("🧪 Testing configuration...")
    
    try:
        # Try to import and validate configuration
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
        from src.config import validate_configuration
        
        config_status = validate_configuration()
        
        if config_status["valid"]:
            print("✅ Configuration is valid!")
            
            settings = config_status["settings"]
            print(f"   • Notion configured: {'✅' if settings['notion_configured'] else '❌'}")
            print(f"   • Google Maps configured: {'✅' if settings['google_maps_configured'] else '❌'}")
            
            return True
        else:
            print(f"❌ Configuration error: {config_status['message']}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing configuration: {e}")
        return False

def main():
    """Main setup function."""
    print("🍽️  Welcome to Restaurant Recommendation MCP Server Setup!\\n")
    
    # Display setup instructions
    print("📚 Please follow these setup instructions first:")
    display_notion_setup_instructions()
    
    input("Press Enter to continue...")
    
    display_google_maps_setup_instructions()
    
    input("Press Enter to continue...")
    
    # Install dependencies
    if not install_dependencies():
        print("❌ Setup failed during dependency installation")
        return 1
    
    # Create .env file
    create_env_file()
    
    # Test configuration
    if test_configuration():
        print("\\n🎉 Setup completed successfully!")
        print("\\n🚀 You can now start the server with:")
        print("   python run_server.py")
        print("\\n🔍 Or check your environment with:")
        print("   python run_server.py --check-env")
        return 0
    else:
        print("\\n❌ Setup completed but configuration is invalid.")
        print("Please check your API keys and try again.")
        return 1

if __name__ == "__main__":
    sys.exit(main())