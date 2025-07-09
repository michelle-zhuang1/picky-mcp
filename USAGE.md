# Restaurant Recommendation MCP Server - Usage Guide

## Quick Start

1. **Setup the environment:**
   ```bash
   python setup.py
   ```

2. **Start the server:**
   ```bash
   python run_server.py
   ```

3. **Test the setup:**
   ```bash
   python run_server.py --check-env
   ```

## MCP Tools Available

### 1. Restaurant Recommendations

**`get_restaurant_recommendations`** - Get personalized restaurant recommendations

**Parameters:**
- `user_id` (optional): User identifier for personalization
- `city`: City for location-based search
- `state` (optional): State for location-based search
- `latitude`/`longitude` (optional): Precise location coordinates
- `occasion` (optional): Dining occasion (casual dining, date night, business lunch, etc.)
- `cuisine_preferences` (optional): Comma-separated cuisine preferences
- `max_distance_km` (optional): Maximum distance in kilometers (default: 25)
- `max_results` (optional): Maximum number of recommendations (default: 10)

**Example:**
```
get_restaurant_recommendations(
    city="Seattle",
    state="WA",
    occasion="date night",
    cuisine_preferences="Italian, Japanese",
    max_distance_km=15,
    max_results=5
)
```

### 2. Restaurant Management

**`add_restaurant_visit`** - Add a new restaurant visit

**Parameters:**
- `restaurant_name`: Name of the restaurant
- `city`: City location
- `state` (optional): State location
- `rating` (optional): Your rating (1-5)
- `cuisine_types` (optional): Comma-separated cuisine types
- `price_range` (optional): Price range ($, $$, $$$, $$$$)
- `vibes` (optional): Comma-separated vibes
- `notes` (optional): Personal notes
- `date_visited` (optional): Date in YYYY-MM-DD format

**Example:**
```
add_restaurant_visit(
    restaurant_name="Joe's Pizza",
    city="New York",
    state="NY",
    rating=4.5,
    cuisine_types="Italian, Pizza",
    price_range="$$",
    vibes="casual, family-friendly",
    notes="Great thin crust pizza"
)
```

**`update_restaurant_rating`** - Update an existing restaurant's rating

**Parameters:**
- `restaurant_name`: Name of the restaurant
- `new_rating`: New rating (1-5)
- `notes` (optional): Updated notes

### 3. Analysis Tools

**`analyze_dining_patterns`** - Analyze your dining patterns and preferences

**Parameters:**
- `user_id` (optional): User identifier

**`find_similar_restaurants`** - Find restaurants similar to one you've enjoyed

**Parameters:**
- `restaurant_name`: Reference restaurant name
- `max_results` (optional): Maximum number of results (default: 5)

### 4. Interactive Sessions

**`start_interactive_session`** - Start a learning session with feedback

**Parameters:**
- `city`: City for recommendations
- `state` (optional): State
- `occasion` (optional): Dining occasion
- `max_distance_km` (optional): Maximum distance

**`provide_session_feedback`** - Provide feedback to improve recommendations

**Parameters:**
- `session_id`: Session identifier
- `liked_restaurant_ids` (optional): Comma-separated liked restaurant IDs
- `disliked_restaurant_ids` (optional): Comma-separated disliked restaurant IDs
- `cuisine_preferences` (optional): Preferred cuisines
- `vibe_preferences` (optional): Preferred vibes

**`get_session_recommendations`** - Get refined recommendations based on feedback

**Parameters:**
- `session_id`: Session identifier

### 5. Database Management

**`enrich_restaurant_database`** - Enrich all restaurants with Google Maps data

**`test_connections`** - Test Notion and Google Maps API connections

## MCP Resources Available

### 1. User Profile

**`profile://dining-preferences`** - Get comprehensive dining profile

**`restaurants://recent-visits`** - Get recent restaurant visits

**`restaurants://favorites`** - Get favorite restaurants (highly rated)

**`restaurants://wishlist`** - Get wishlist restaurants

### 2. Restaurant Database

**`restaurants://database`** - Get complete restaurant database

**`config://status`** - Get server status and configuration

## Usage Examples

### Planning a Date Night

```python
# Get romantic restaurant recommendations
recommendations = get_restaurant_recommendations(
    city="San Francisco",
    state="CA",
    occasion="date night",
    cuisine_preferences="Italian, French",
    max_distance_km=10,
    max_results=5
)
```

### Adding a Restaurant Visit

```python
# Add a new restaurant visit
add_restaurant_visit(
    restaurant_name="Le Bernardin",
    city="New York",
    state="NY",
    rating=5,
    cuisine_types="French, Seafood",
    price_range="$$$$",
    vibes="fine dining, romantic",
    notes="Exceptional seafood, perfect for special occasions"
)
```

### Interactive Learning Session

```python
# Start a session
session = start_interactive_session(
    city="Chicago",
    state="IL",
    occasion="casual dining"
)

# Provide feedback
provide_session_feedback(
    session_id=session["session_id"],
    liked_restaurant_ids="restaurant_1,restaurant_3",
    disliked_restaurant_ids="restaurant_2",
    cuisine_preferences="Italian, Thai",
    vibe_preferences="casual, cozy"
)

# Get refined recommendations
refined_recs = get_session_recommendations(
    session_id=session["session_id"]
)
```

### Analyzing Your Dining Patterns

```python
# Get detailed analysis
analysis = analyze_dining_patterns()
# Returns cuisine preferences, price comfort zone, dining personality, etc.

# Find similar restaurants
similar = find_similar_restaurants(
    restaurant_name="Alinea",
    max_results=3
)
```

## Configuration

### Environment Variables

Create a `.env` file with:

```bash
# Notion API Configuration
NOTION_API_KEY=your_notion_integration_token
NOTION_DATABASE_ID=your_restaurant_database_id

# Google Maps API Configuration
GOOGLE_MAPS_API_KEY=your_google_maps_api_key

# Server Configuration
DEBUG=false
MAX_RECOMMENDATIONS=10
DEFAULT_SEARCH_RADIUS_KM=25.0
```

### Notion Database Schema

Your Notion database should have these properties:

**Required:**
- Name (Title)
- City (Text)

**Recommended:**
- Rating (Number)
- Cuisine (Multi-select)
- Location (Text)
- State (Text)
- Date Visited (Date)
- Notes (Text)
- Google Place ID (Text)
- Price Range (Select: $, $$, $$$, $$$$)
- Vibes (Multi-select)
- Revisit (Checkbox)
- Wishlist (Checkbox)

## Supported Cuisine Types

- American, Italian, Japanese, Chinese, Mexican, Indian, French, Thai
- Mediterranean, Seafood, Steakhouse, Pizza, Sushi, Barbecue
- Vegetarian, Vegan, Fast Food, Cafe, Bakery, Other

## Supported Vibes

- casual, romantic, family-friendly, fine dining, trendy, cozy
- lively, quiet, outdoor, sports bar, date night, business, brunch, late night

## Supported Occasions

- casual dining, date night, business lunch, family dinner, celebration
- quick bite, weekend brunch, happy hour, late night, takeout

## Troubleshooting

### Common Issues

1. **"Configuration error"**
   - Check your `.env` file has all required API keys
   - Verify API keys are valid and active

2. **"No recommendations found"**
   - Try expanding search radius
   - Check if you have restaurants in the database
   - Verify location spelling

3. **"Restaurant not found"**
   - Check restaurant name spelling
   - Ensure restaurant exists in your Notion database

4. **"Session not found"**
   - Verify session ID is correct
   - Sessions may expire after inactivity

### Debug Mode

Run with debug logging:
```bash
python run_server.py --debug
```

### Testing Configuration

```bash
python run_server.py --check-env
```

## Advanced Features

### Automatic Data Enrichment

The server automatically enriches your restaurant data with:
- Google Maps ratings and reviews
- Accurate location coordinates
- Business hours and contact information
- Restaurant photos and additional details

### Real-time Learning

Interactive sessions learn from your feedback:
- Cuisine preferences are updated based on likes/dislikes
- Vibe preferences are refined over time
- Price sensitivity is learned from your choices

### Personalized Profiles

The system builds detailed profiles including:
- Dining personality (Adventurous Eater, Fine Dining Enthusiast, etc.)
- Cuisine preferences with frequency and ratings
- Price comfort zones
- Location patterns and preferences

This system integrates seamlessly with your existing Picky restaurant recommendation system while providing powerful MCP capabilities for Claude to help you discover and manage your dining experiences.