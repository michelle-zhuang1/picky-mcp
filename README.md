# Picky MCP Server

A Model Context Protocol (MCP) server that provides intelligent restaurant recommendations by integrating with Notion's API for restaurant database management and Google Maps for location enrichment.

## Features

- **Notion Integration**: Read and write to your restaurant database in Notion
- **Google Maps Integration**: Automatic restaurant data enrichment and location services
- **Real-time Profile Updates**: Dynamic user profile management based on Notion changes
- **Smart Recommendations**: Context-aware restaurant suggestions for different occasions
- **Automated Data Enrichment**: Automatically populate restaurant details from Google Maps

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys
```

3. Run the server:
```bash
python src/server.py
```

## Configuration

### Notion Setup
1. Create a new integration at https://www.notion.so/my-integrations
2. Copy the integration token to your `.env` file
3. Share your restaurant database with the integration
4. Copy the database ID to your `.env` file

### Google Maps Setup
1. Go to Google Cloud Console
2. Enable the Places API
3. Create an API key
4. Add the API key to your `.env` file

## Usage

Once running, the MCP server provides tools and resources for:

- Getting personalized restaurant recommendations
- Managing restaurant visits and ratings
- Analyzing dining patterns
- Enriching restaurant data automatically
- Finding similar restaurants

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   MCP Client    │────│  MCP Server      │────│  Notion API     │
│   (Claude)      │    │  (Restaurant     │    │  (Database)     │
└─────────────────┘    │   Manager)       │    └─────────────────┘
                       │                  │    
                       │                  │    ┌─────────────────┐
                       │                  │────│ Google Maps API │
                       └──────────────────┘    │ (Enrichment)    │
                                               └─────────────────┘
```