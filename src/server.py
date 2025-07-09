"""Main MCP server implementation for restaurant recommendations."""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import json
import uuid

from mcp.server.fastmcp import FastMCP
from mcp.server.session import RequestContext

from .config import settings, validate_configuration
from .models import (
    Restaurant, Location, RecommendationContext, CuisineType, 
    PriceRange, VibeType, OccasionType, SessionFeedback
)
from .notion_client import NotionManager
from .maps_client import GoogleMapsClient
from .restaurant_manager import RestaurantManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize MCP server
mcp = FastMCP("Restaurant Recommendation Server")

# Initialize components
notion_client = NotionManager()
maps_client = GoogleMapsClient()
restaurant_manager = RestaurantManager(notion_client, maps_client)

# Server startup and status
@mcp.resource("config://status")
def get_server_status() -> str:
    """Get the current server status and configuration."""
    config_status = validate_configuration()
    
    status_info = {
        "server": "Restaurant Recommendation MCP Server",
        "version": "0.1.0",
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "configuration": config_status
    }
    
    return json.dumps(status_info, indent=2)

@mcp.resource("profile://dining-preferences")
def get_dining_profile(user_id: str = "default") -> str:
    """Get comprehensive dining profile for a user."""
    try:
        profile = asyncio.run(restaurant_manager.generate_dining_profile(user_id))
        return profile
    except Exception as e:
        logger.error(f"Failed to get dining profile: {e}")
        return f"Error retrieving dining profile: {str(e)}"

@mcp.resource("restaurants://recent-visits")
def get_recent_visits(user_id: str = "default", limit: int = 10) -> str:
    """Get recent restaurant visits."""
    try:
        restaurants = asyncio.run(notion_client.get_recent_visits(limit))
        
        if not restaurants:
            return "No recent visits found."
        
        visits_info = []
        for restaurant in restaurants:
            visit_info = {
                "name": restaurant.name,
                "location": f"{restaurant.location.city}, {restaurant.location.state}",
                "rating": restaurant.personal_rating,
                "date_visited": restaurant.date_visited.isoformat() if restaurant.date_visited else None,
                "cuisine_types": [c.value for c in restaurant.cuisine_types],
                "notes": restaurant.notes
            }
            visits_info.append(visit_info)
        
        return json.dumps(visits_info, indent=2)
    except Exception as e:
        logger.error(f"Failed to get recent visits: {e}")
        return f"Error retrieving recent visits: {str(e)}"

@mcp.resource("restaurants://favorites")
def get_favorite_restaurants(user_id: str = "default", min_rating: float = 4.0) -> str:
    """Get favorite restaurants (highly rated)."""
    try:
        restaurants = asyncio.run(notion_client.get_favorites(min_rating))
        
        if not restaurants:
            return f"No restaurants with rating >= {min_rating} found."
        
        favorites_info = []
        for restaurant in restaurants:
            favorite_info = {
                "name": restaurant.name,
                "location": f"{restaurant.location.city}, {restaurant.location.state}",
                "rating": restaurant.personal_rating,
                "cuisine_types": [c.value for c in restaurant.cuisine_types],
                "vibes": [v.value for v in restaurant.vibes],
                "notes": restaurant.notes
            }
            favorites_info.append(favorite_info)
        
        return json.dumps(favorites_info, indent=2)
    except Exception as e:
        logger.error(f"Failed to get favorites: {e}")
        return f"Error retrieving favorites: {str(e)}"

@mcp.resource("restaurants://wishlist")
def get_wishlist_restaurants(user_id: str = "default") -> str:
    """Get wishlist restaurants."""
    try:
        restaurants = asyncio.run(notion_client.get_wishlist())
        
        if not restaurants:
            return "No wishlist restaurants found."
        
        wishlist_info = []
        for restaurant in restaurants:
            wishlist_item = {
                "name": restaurant.name,
                "location": f"{restaurant.location.city}, {restaurant.location.state}",
                "cuisine_types": [c.value for c in restaurant.cuisine_types],
                "vibes": [v.value for v in restaurant.vibes],
                "notes": restaurant.notes,
                "google_rating": restaurant.google_places_data.rating if restaurant.google_places_data else None
            }
            wishlist_info.append(wishlist_item)
        
        return json.dumps(wishlist_info, indent=2)
    except Exception as e:
        logger.error(f"Failed to get wishlist: {e}")
        return f"Error retrieving wishlist: {str(e)}"

@mcp.resource("restaurants://database")
def get_restaurant_database(user_id: str = "default") -> str:
    """Get complete restaurant database."""
    try:
        restaurants = asyncio.run(notion_client.get_all_restaurants())
        
        database_info = {
            "total_restaurants": len(restaurants),
            "last_updated": datetime.now().isoformat(),
            "restaurants": []
        }
        
        for restaurant in restaurants:
            restaurant_info = {
                "id": restaurant.id,
                "name": restaurant.name,
                "location": {
                    "city": restaurant.location.city,
                    "state": restaurant.location.state,
                    "address": restaurant.location.address
                },
                "cuisine_types": [c.value for c in restaurant.cuisine_types],
                "price_range": restaurant.price_range.value if restaurant.price_range else None,
                "vibes": [v.value for v in restaurant.vibes],
                "personal_rating": restaurant.personal_rating,
                "date_visited": restaurant.date_visited.isoformat() if restaurant.date_visited else None,
                "is_wishlist": restaurant.is_wishlist,
                "notes": restaurant.notes
            }
            database_info["restaurants"].append(restaurant_info)
        
        return json.dumps(database_info, indent=2)
    except Exception as e:
        logger.error(f"Failed to get restaurant database: {e}")
        return f"Error retrieving restaurant database: {str(e)}"

# Restaurant recommendation tools
@mcp.tool()
def get_restaurant_recommendations(
    user_id: str = "default",
    city: str = None,
    state: str = None,
    latitude: float = None,
    longitude: float = None,
    occasion: str = "casual dining",
    cuisine_preferences: str = None,
    max_distance_km: float = 25.0,
    max_results: int = 10
) -> str:
    """Get personalized restaurant recommendations based on preferences and context.
    
    Args:
        user_id: User identifier for personalization
        city: City for location-based search
        state: State for location-based search
        latitude: Latitude for precise location search
        longitude: Longitude for precise location search
        occasion: Type of dining occasion (casual dining, date night, business lunch, etc.)
        cuisine_preferences: Comma-separated cuisine preferences
        max_distance_km: Maximum distance for recommendations in kilometers
        max_results: Maximum number of recommendations to return
    """
    try:
        # Build location
        if latitude and longitude:
            location = Location(
                city=city or "Unknown",
                state=state,
                latitude=latitude,
                longitude=longitude
            )
        elif city:
            location = Location(
                city=city,
                state=state
            )
        else:
            return "Error: Either city or latitude/longitude must be provided"
        
        # Parse cuisine preferences
        cuisine_list = []
        if cuisine_preferences:
            cuisine_names = [c.strip() for c in cuisine_preferences.split(",")]
            for cuisine_name in cuisine_names:
                try:
                    cuisine_list.append(CuisineType(cuisine_name))
                except ValueError:
                    logger.warning(f"Invalid cuisine type: {cuisine_name}")
        
        # Parse occasion
        try:
            occasion_type = OccasionType(occasion)
        except ValueError:
            occasion_type = OccasionType.CASUAL_DINING
        
        # Build recommendation context
        context = RecommendationContext(
            user_id=user_id,
            location=location,
            occasion=occasion_type,
            max_distance_km=max_distance_km,
            max_results=max_results,
            cuisine_preferences=cuisine_list
        )
        
        # Get recommendations
        recommendations = asyncio.run(restaurant_manager.get_recommendations(user_id, context))
        
        if not recommendations:
            return f"No recommendations found for {location.city}. Try expanding your search radius or adjusting preferences."
        
        # Format recommendations
        rec_info = {
            "context": {
                "location": f"{location.city}, {location.state}",
                "occasion": occasion,
                "cuisine_preferences": cuisine_preferences,
                "max_distance_km": max_distance_km
            },
            "recommendations": []
        }
        
        for rec in recommendations:
            rec_data = {
                "name": rec.restaurant.name,
                "score": round(rec.score, 2),
                "reasoning": rec.reasoning,
                "location": {
                    "city": rec.restaurant.location.city,
                    "state": rec.restaurant.location.state,
                    "address": rec.restaurant.location.address
                },
                "cuisine_types": [c.value for c in rec.restaurant.cuisine_types],
                "price_range": rec.restaurant.price_range.value if rec.restaurant.price_range else None,
                "vibes": [v.value for v in rec.restaurant.vibes],
                "distance_km": round(rec.distance_km, 1) if rec.distance_km else None,
                "google_rating": rec.restaurant.google_places_data.rating if rec.restaurant.google_places_data else None,
                "is_wishlist": rec.restaurant.is_wishlist
            }
            rec_info["recommendations"].append(rec_data)
        
        return json.dumps(rec_info, indent=2)
    except Exception as e:
        logger.error(f"Failed to get recommendations: {e}")
        return f"Error getting recommendations: {str(e)}"

@mcp.tool()
def add_restaurant_visit(
    user_id: str = "default",
    restaurant_name: str = None,
    city: str = None,
    state: str = None,
    rating: float = None,
    cuisine_types: str = None,
    price_range: str = None,
    vibes: str = None,
    notes: str = None,
    date_visited: str = None
) -> str:
    """Add a new restaurant visit to your Notion database.
    
    Args:
        user_id: User identifier
        restaurant_name: Name of the restaurant
        city: City where restaurant is located
        state: State where restaurant is located
        rating: Your rating (1-5 stars)
        cuisine_types: Comma-separated cuisine types
        price_range: Price range ($, $$, $$$, $$$$)
        vibes: Comma-separated vibes/atmosphere
        notes: Personal notes about the restaurant
        date_visited: Date visited (YYYY-MM-DD format)
    """
    try:
        if not restaurant_name:
            return "Error: Restaurant name is required"
        
        if not city:
            return "Error: City is required"
        
        # Build location
        location = Location(city=city, state=state)
        
        # Parse cuisine types
        cuisine_list = []
        if cuisine_types:
            cuisine_names = [c.strip() for c in cuisine_types.split(",")]
            for cuisine_name in cuisine_names:
                try:
                    cuisine_list.append(CuisineType(cuisine_name))
                except ValueError:
                    logger.warning(f"Invalid cuisine type: {cuisine_name}")
        
        # Parse price range
        price_range_enum = None
        if price_range:
            try:
                price_range_enum = PriceRange(price_range)
            except ValueError:
                logger.warning(f"Invalid price range: {price_range}")
        
        # Parse vibes
        vibe_list = []
        if vibes:
            vibe_names = [v.strip() for v in vibes.split(",")]
            for vibe_name in vibe_names:
                try:
                    vibe_list.append(VibeType(vibe_name))
                except ValueError:
                    logger.warning(f"Invalid vibe type: {vibe_name}")
        
        # Parse date
        visit_date = None
        if date_visited:
            try:
                visit_date = datetime.fromisoformat(date_visited)
            except ValueError:
                logger.warning(f"Invalid date format: {date_visited}")
        
        # Create restaurant
        restaurant = Restaurant(
            name=restaurant_name,
            location=location,
            cuisine_types=cuisine_list,
            price_range=price_range_enum,
            vibes=vibe_list,
            personal_rating=rating,
            notes=notes,
            date_visited=visit_date or datetime.now()
        )
        
        # Add to Notion
        result = asyncio.run(notion_client.add_restaurant(restaurant))
        
        if result["success"]:
            # Try to enrich with Google Maps data
            try:
                enriched_restaurant = asyncio.run(maps_client.enrich_restaurant_data(restaurant))
                if enriched_restaurant.google_places_data:
                    asyncio.run(notion_client.update_restaurant(result["page_id"], enriched_restaurant))
            except Exception as e:
                logger.warning(f"Failed to enrich restaurant data: {e}")
            
            return f"✅ Successfully added {restaurant_name} to your restaurant database!"
        else:
            return f"❌ Failed to add restaurant: {result.get('error', 'Unknown error')}"
    
    except Exception as e:
        logger.error(f"Failed to add restaurant visit: {e}")
        return f"Error adding restaurant visit: {str(e)}"

@mcp.tool()
def update_restaurant_rating(
    user_id: str = "default",
    restaurant_name: str = None,
    new_rating: float = None,
    notes: str = None
) -> str:
    """Update rating for an existing restaurant.
    
    Args:
        user_id: User identifier
        restaurant_name: Name of the restaurant to update
        new_rating: New rating (1-5 stars)
        notes: Updated notes
    """
    try:
        if not restaurant_name:
            return "Error: Restaurant name is required"
        
        if not new_rating:
            return "Error: New rating is required"
        
        # Find restaurant
        restaurant = asyncio.run(notion_client.get_restaurant_by_name(restaurant_name))
        if not restaurant:
            return f"Restaurant '{restaurant_name}' not found in your database"
        
        # Update rating
        restaurant.personal_rating = new_rating
        if notes:
            restaurant.notes = notes
        restaurant.updated_at = datetime.now()
        
        # Update in Notion
        result = asyncio.run(notion_client.update_restaurant(restaurant.notion_page_id, restaurant))
        
        if result["success"]:
            return f"✅ Updated rating for {restaurant_name} to {new_rating} stars"
        else:
            return f"❌ Failed to update restaurant: {result.get('error', 'Unknown error')}"
    
    except Exception as e:
        logger.error(f"Failed to update restaurant rating: {e}")
        return f"Error updating restaurant rating: {str(e)}"

@mcp.tool()
def analyze_dining_patterns(user_id: str = "default") -> str:
    """Analyze your dining patterns and preferences.
    
    Args:
        user_id: User identifier
    """
    try:
        analysis = asyncio.run(restaurant_manager.analyze_dining_patterns(user_id))
        
        if "error" in analysis:
            return f"Error analyzing dining patterns: {analysis['error']}"
        
        return json.dumps(analysis, indent=2)
    
    except Exception as e:
        logger.error(f"Failed to analyze dining patterns: {e}")
        return f"Error analyzing dining patterns: {str(e)}"

@mcp.tool()
def find_similar_restaurants(
    user_id: str = "default",
    restaurant_name: str = None,
    max_results: int = 5
) -> str:
    """Find restaurants similar to one you've enjoyed.
    
    Args:
        user_id: User identifier
        restaurant_name: Name of the reference restaurant
        max_results: Maximum number of similar restaurants to return
    """
    try:
        if not restaurant_name:
            return "Error: Restaurant name is required"
        
        similar_restaurants = asyncio.run(
            restaurant_manager.find_similar_restaurants(restaurant_name, user_id, max_results)
        )
        
        if not similar_restaurants:
            return f"No similar restaurants found for '{restaurant_name}'"
        
        similar_info = {
            "reference_restaurant": restaurant_name,
            "similar_restaurants": []
        }
        
        for rec in similar_restaurants:
            similar_data = {
                "name": rec.restaurant.name,
                "similarity_score": round(rec.score, 2),
                "reasoning": rec.reasoning,
                "location": f"{rec.restaurant.location.city}, {rec.restaurant.location.state}",
                "cuisine_types": [c.value for c in rec.restaurant.cuisine_types],
                "vibes": [v.value for v in rec.restaurant.vibes],
                "your_rating": rec.restaurant.personal_rating
            }
            similar_info["similar_restaurants"].append(similar_data)
        
        return json.dumps(similar_info, indent=2)
    
    except Exception as e:
        logger.error(f"Failed to find similar restaurants: {e}")
        return f"Error finding similar restaurants: {str(e)}"

@mcp.tool()
def enrich_restaurant_database(user_id: str = "default") -> str:
    """Automatically enrich all restaurants with Google Maps data.
    
    Args:
        user_id: User identifier
    """
    try:
        result = asyncio.run(restaurant_manager.enrich_restaurant_database())
        
        if result["success"]:
            return f"✅ Database enrichment completed! {result['message']}"
        else:
            return f"❌ Database enrichment failed: {result.get('error', 'Unknown error')}"
    
    except Exception as e:
        logger.error(f"Failed to enrich restaurant database: {e}")
        return f"Error enriching restaurant database: {str(e)}"

@mcp.tool()
def start_interactive_session(
    user_id: str = "default",
    city: str = None,
    state: str = None,
    occasion: str = "casual dining",
    max_distance_km: float = 25.0
) -> str:
    """Start an interactive recommendation session with feedback learning.
    
    Args:
        user_id: User identifier
        city: City for location-based search
        state: State for location-based search
        occasion: Type of dining occasion
        max_distance_km: Maximum distance for recommendations in kilometers
    """
    try:
        if not city:
            return "Error: City is required"
        
        # Build location
        location = Location(city=city, state=state)
        
        # Parse occasion
        try:
            occasion_type = OccasionType(occasion)
        except ValueError:
            occasion_type = OccasionType.CASUAL_DINING
        
        # Build recommendation context
        context = RecommendationContext(
            user_id=user_id,
            location=location,
            occasion=occasion_type,
            max_distance_km=max_distance_km,
            max_results=5  # Start with fewer recommendations for interactive session
        )
        
        # Start session
        session = asyncio.run(restaurant_manager.start_interactive_session(user_id, context))
        
        session_info = {
            "session_id": session.session_id,
            "user_id": session.user_id,
            "location": f"{location.city}, {location.state}",
            "occasion": occasion,
            "initial_recommendations": []
        }
        
        for rec in session.recommendations:
            rec_data = {
                "restaurant_id": rec.restaurant.id,
                "name": rec.restaurant.name,
                "score": round(rec.score, 2),
                "reasoning": rec.reasoning,
                "cuisine_types": [c.value for c in rec.restaurant.cuisine_types],
                "vibes": [v.value for v in rec.restaurant.vibes]
            }
            session_info["initial_recommendations"].append(rec_data)
        
        return json.dumps(session_info, indent=2)
    
    except Exception as e:
        logger.error(f"Failed to start interactive session: {e}")
        return f"Error starting interactive session: {str(e)}"

@mcp.tool()
def provide_session_feedback(
    session_id: str = None,
    liked_restaurant_ids: str = None,
    disliked_restaurant_ids: str = None,
    cuisine_preferences: str = None,
    vibe_preferences: str = None,
    additional_notes: str = None
) -> str:
    """Provide feedback for an interactive recommendation session.
    
    Args:
        session_id: Session identifier
        liked_restaurant_ids: Comma-separated restaurant IDs you liked
        disliked_restaurant_ids: Comma-separated restaurant IDs you disliked
        cuisine_preferences: Comma-separated cuisine preferences
        vibe_preferences: Comma-separated vibe preferences
        additional_notes: Additional feedback notes
    """
    try:
        if not session_id:
            return "Error: Session ID is required"
        
        # Parse liked/disliked restaurants
        liked_ids = []
        if liked_restaurant_ids:
            liked_ids = [id.strip() for id in liked_restaurant_ids.split(",")]
        
        disliked_ids = []
        if disliked_restaurant_ids:
            disliked_ids = [id.strip() for id in disliked_restaurant_ids.split(",")]
        
        # Parse cuisine feedback
        cuisine_feedback = {}
        if cuisine_preferences:
            cuisine_names = [c.strip() for c in cuisine_preferences.split(",")]
            for cuisine_name in cuisine_names:
                try:
                    cuisine_feedback[CuisineType(cuisine_name)] = 5.0  # High preference
                except ValueError:
                    logger.warning(f"Invalid cuisine type: {cuisine_name}")
        
        # Parse vibe feedback
        vibe_feedback = {}
        if vibe_preferences:
            vibe_names = [v.strip() for v in vibe_preferences.split(",")]
            for vibe_name in vibe_names:
                try:
                    vibe_feedback[VibeType(vibe_name)] = 5.0  # High preference
                except ValueError:
                    logger.warning(f"Invalid vibe type: {vibe_name}")
        
        # Create feedback
        feedback = SessionFeedback(
            session_id=session_id,
            liked_restaurants=liked_ids,
            disliked_restaurants=disliked_ids,
            cuisine_feedback=cuisine_feedback,
            vibe_feedback=vibe_feedback,
            additional_notes=additional_notes
        )
        
        # Process feedback
        result = asyncio.run(restaurant_manager.process_session_feedback(session_id, feedback))
        
        if result["success"]:
            return f"✅ Feedback processed successfully! Your preferences have been updated."
        else:
            return f"❌ Failed to process feedback: {result.get('error', 'Unknown error')}"
    
    except Exception as e:
        logger.error(f"Failed to provide session feedback: {e}")
        return f"Error providing session feedback: {str(e)}"

@mcp.tool()
def get_session_recommendations(session_id: str = None) -> str:
    """Get refined recommendations based on session feedback.
    
    Args:
        session_id: Session identifier
    """
    try:
        if not session_id:
            return "Error: Session ID is required"
        
        recommendations = asyncio.run(restaurant_manager.get_session_recommendations(session_id))
        
        if not recommendations:
            return "No recommendations found for this session"
        
        rec_info = {
            "session_id": session_id,
            "refined_recommendations": []
        }
        
        for rec in recommendations:
            rec_data = {
                "restaurant_id": rec.restaurant.id,
                "name": rec.restaurant.name,
                "score": round(rec.score, 2),
                "reasoning": rec.reasoning,
                "location": f"{rec.restaurant.location.city}, {rec.restaurant.location.state}",
                "cuisine_types": [c.value for c in rec.restaurant.cuisine_types],
                "vibes": [v.value for v in rec.restaurant.vibes]
            }
            rec_info["refined_recommendations"].append(rec_data)
        
        return json.dumps(rec_info, indent=2)
    
    except Exception as e:
        logger.error(f"Failed to get session recommendations: {e}")
        return f"Error getting session recommendations: {str(e)}"

@mcp.tool()
def test_connections(user_id: str = "default") -> str:
    """Test connections to Notion and Google Maps APIs.
    
    Args:
        user_id: User identifier
    """
    try:
        results = {
            "notion": asyncio.run(notion_client.test_connection()),
            "google_maps": maps_client.test_connection(),
            "timestamp": datetime.now().isoformat()
        }
        
        return json.dumps(results, indent=2)
    
    except Exception as e:
        logger.error(f"Failed to test connections: {e}")
        return f"Error testing connections: {str(e)}"

def main():
    """Main function to run the MCP server."""
    logger.info("Starting Restaurant Recommendation MCP Server...")
    
    # Validate configuration
    config_status = validate_configuration()
    if not config_status["valid"]:
        logger.error(f"Configuration error: {config_status['message']}")
        return
    
    logger.info("Configuration validated successfully")
    logger.info(f"Notion configured: {config_status['settings']['notion_configured']}")
    logger.info(f"Google Maps configured: {config_status['settings']['google_maps_configured']}")
    
    # Run the server
    logger.info("MCP Server ready to accept connections")
    
if __name__ == "__main__":
    main()