"""Notion API client for restaurant database operations."""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio
from notion_client import AsyncClient
from notion_client.errors import NotionClientError

from .models import (
    Restaurant, Location, CuisineType, PriceRange, VibeType,
    GooglePlacesData, NotionDatabaseSchema
)
from .config import settings

logger = logging.getLogger(__name__)


class NotionManager:
    """Manages Notion API interactions for restaurant data."""
    
    def __init__(self, api_key: str = None, database_id: str = None):
        """Initialize Notion client."""
        self.api_key = api_key or settings.notion_api_key
        self.database_id = database_id or settings.notion_database_id
        self.client = AsyncClient(auth=self.api_key)
        self.schema = NotionDatabaseSchema(database_id=self.database_id)
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test Notion API connection."""
        try:
            # Test by retrieving database info
            database = await self.client.databases.retrieve(self.database_id)
            return {
                "success": True,
                "database_title": database.get("title", [{}])[0].get("plain_text", "Unknown"),
                "database_id": self.database_id
            }
        except Exception as e:
            logger.error(f"Notion connection test failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def add_restaurant(self, restaurant: Restaurant) -> Dict[str, Any]:
        """Add a new restaurant to Notion database."""
        try:
            properties = self._build_notion_properties(restaurant)
            
            response = await self.client.pages.create(
                parent={"database_id": self.database_id},
                properties=properties
            )
            
            restaurant.notion_page_id = response["id"]
            
            return {
                "success": True,
                "page_id": response["id"],
                "restaurant_id": restaurant.id,
                "message": f"Added restaurant '{restaurant.name}' to Notion database"
            }
        except NotionClientError as e:
            logger.error(f"Failed to add restaurant to Notion: {e}")
            return {"success": False, "error": str(e)}
    
    async def update_restaurant(self, page_id: str, restaurant: Restaurant) -> Dict[str, Any]:
        """Update existing restaurant in Notion database."""
        try:
            properties = self._build_notion_properties(restaurant)
            
            response = await self.client.pages.update(
                page_id=page_id,
                properties=properties
            )
            
            return {
                "success": True,
                "page_id": page_id,
                "message": f"Updated restaurant '{restaurant.name}' in Notion database"
            }
        except NotionClientError as e:
            logger.error(f"Failed to update restaurant in Notion: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_restaurant_by_id(self, page_id: str) -> Optional[Restaurant]:
        """Get restaurant by Notion page ID."""
        try:
            response = await self.client.pages.retrieve(page_id)
            return self._parse_notion_page_to_restaurant(response)
        except NotionClientError as e:
            logger.error(f"Failed to get restaurant by ID: {e}")
            return None
    
    async def get_restaurant_by_name(self, name: str) -> Optional[Restaurant]:
        """Find restaurant by name."""
        try:
            response = await self.client.databases.query(
                database_id=self.database_id,
                filter={
                    "property": "Name",
                    "title": {"equals": name}
                }
            )
            
            if response["results"]:
                return self._parse_notion_page_to_restaurant(response["results"][0])
            return None
        except NotionClientError as e:
            logger.error(f"Failed to get restaurant by name: {e}")
            return None
    
    async def query_restaurants(self, filters: Dict[str, Any] = None, limit: int = 100) -> List[Restaurant]:
        """Query restaurants with optional filters."""
        try:
            query_params = {
                "database_id": self.database_id,
                "page_size": min(limit, 100)
            }
            
            if filters:
                query_params["filter"] = self._build_notion_filter(filters)
            
            response = await self.client.databases.query(**query_params)
            
            restaurants = []
            for page in response["results"]:
                restaurant = self._parse_notion_page_to_restaurant(page)
                if restaurant:
                    restaurants.append(restaurant)
            
            return restaurants
        except NotionClientError as e:
            logger.error(f"Failed to query restaurants: {e}")
            return []
    
    async def get_all_restaurants(self) -> List[Restaurant]:
        """Get all restaurants from Notion database."""
        return await self.query_restaurants()
    
    async def get_recent_visits(self, limit: int = 10) -> List[Restaurant]:
        """Get recently visited restaurants."""
        try:
            response = await self.client.databases.query(
                database_id=self.database_id,
                filter={
                    "property": "Date Visited",
                    "date": {"is_not_empty": True}
                },
                sorts=[{
                    "property": "Date Visited",
                    "direction": "descending"
                }],
                page_size=limit
            )
            
            restaurants = []
            for page in response["results"]:
                restaurant = self._parse_notion_page_to_restaurant(page)
                if restaurant:
                    restaurants.append(restaurant)
            
            return restaurants
        except NotionClientError as e:
            logger.error(f"Failed to get recent visits: {e}")
            return []
    
    async def get_favorites(self, min_rating: float = 4.0, limit: int = 20) -> List[Restaurant]:
        """Get favorite restaurants (highly rated)."""
        try:
            response = await self.client.databases.query(
                database_id=self.database_id,
                filter={
                    "property": "Rating",
                    "number": {"greater_than_or_equal_to": min_rating}
                },
                sorts=[{
                    "property": "Rating",
                    "direction": "descending"
                }],
                page_size=limit
            )
            
            restaurants = []
            for page in response["results"]:
                restaurant = self._parse_notion_page_to_restaurant(page)
                if restaurant:
                    restaurants.append(restaurant)
            
            return restaurants
        except NotionClientError as e:
            logger.error(f"Failed to get favorites: {e}")
            return []
    
    async def get_wishlist(self, limit: int = 50) -> List[Restaurant]:
        """Get wishlist restaurants."""
        try:
            response = await self.client.databases.query(
                database_id=self.database_id,
                filter={
                    "property": "Wishlist",
                    "checkbox": {"equals": True}
                },
                page_size=limit
            )
            
            restaurants = []
            for page in response["results"]:
                restaurant = self._parse_notion_page_to_restaurant(page)
                if restaurant:
                    restaurants.append(restaurant)
            
            return restaurants
        except NotionClientError as e:
            logger.error(f"Failed to get wishlist: {e}")
            return []
    
    def _build_notion_properties(self, restaurant: Restaurant) -> Dict[str, Any]:
        """Build Notion properties from restaurant model."""
        properties = {
            "Name": {"title": [{"text": {"content": restaurant.name}}]},
            "City": {"rich_text": [{"text": {"content": restaurant.location.city}}]},
        }
        
        if restaurant.location.state:
            properties["State"] = {"rich_text": [{"text": {"content": restaurant.location.state}}]}
        
        if restaurant.location.address:
            properties["Location"] = {"rich_text": [{"text": {"content": restaurant.location.address}}]}
        
        if restaurant.personal_rating:
            properties["Rating"] = {"number": restaurant.personal_rating}
        
        if restaurant.cuisine_types:
            properties["Cuisine"] = {
                "multi_select": [{"name": cuisine.value} for cuisine in restaurant.cuisine_types]
            }
        
        if restaurant.price_range:
            properties["Price Range"] = {"select": {"name": restaurant.price_range.value}}
        
        if restaurant.vibes:
            properties["Vibes"] = {
                "multi_select": [{"name": vibe.value} for vibe in restaurant.vibes]
            }
        
        if restaurant.notes:
            properties["Notes"] = {"rich_text": [{"text": {"content": restaurant.notes}}]}
        
        if restaurant.date_visited:
            properties["Date Visited"] = {"date": {"start": restaurant.date_visited.isoformat()}}
        
        if restaurant.revisit is not None:
            properties["Revisit"] = {"checkbox": restaurant.revisit}
        
        properties["Wishlist"] = {"checkbox": restaurant.is_wishlist}
        
        if restaurant.google_places_data and restaurant.google_places_data.place_id:
            properties["Google Place ID"] = {
                "rich_text": [{"text": {"content": restaurant.google_places_data.place_id}}]
            }
        
        return properties
    
    def _parse_notion_page_to_restaurant(self, page: Dict[str, Any]) -> Optional[Restaurant]:
        """Parse Notion page to restaurant model."""
        try:
            properties = page.get("properties", {})
            
            # Required fields
            name_prop = properties.get("Name", {})
            name = name_prop.get("title", [{}])[0].get("plain_text", "")
            
            city_prop = properties.get("City", {})
            city = city_prop.get("rich_text", [{}])[0].get("plain_text", "")
            
            if not name or not city:
                return None
            
            # Location
            location_prop = properties.get("Location", {})
            address = location_prop.get("rich_text", [{}])[0].get("plain_text", "")
            
            state_prop = properties.get("State", {})
            state = state_prop.get("rich_text", [{}])[0].get("plain_text", "")
            
            location = Location(
                address=address or None,
                city=city,
                state=state or None
            )
            
            # Rating
            rating_prop = properties.get("Rating", {})
            rating = rating_prop.get("number")
            
            # Cuisine types
            cuisine_prop = properties.get("Cuisine", {})
            cuisine_types = []
            for cuisine_option in cuisine_prop.get("multi_select", []):
                try:
                    cuisine_types.append(CuisineType(cuisine_option["name"]))
                except ValueError:
                    pass  # Skip invalid cuisine types
            
            # Price range
            price_prop = properties.get("Price Range", {})
            price_range = None
            if price_prop.get("select"):
                try:
                    price_range = PriceRange(price_prop["select"]["name"])
                except ValueError:
                    pass
            
            # Vibes
            vibes_prop = properties.get("Vibes", {})
            vibes = []
            for vibe_option in vibes_prop.get("multi_select", []):
                try:
                    vibes.append(VibeType(vibe_option["name"]))
                except ValueError:
                    pass  # Skip invalid vibe types
            
            # Notes
            notes_prop = properties.get("Notes", {})
            notes = notes_prop.get("rich_text", [{}])[0].get("plain_text", "")
            
            # Date visited
            date_prop = properties.get("Date Visited", {})
            date_visited = None
            if date_prop.get("date") and date_prop["date"].get("start"):
                try:
                    date_visited = datetime.fromisoformat(date_prop["date"]["start"])
                except ValueError:
                    pass
            
            # Revisit
            revisit_prop = properties.get("Revisit", {})
            revisit = revisit_prop.get("checkbox")
            
            # Wishlist
            wishlist_prop = properties.get("Wishlist", {})
            is_wishlist = wishlist_prop.get("checkbox", False)
            
            # Google Places data
            google_place_id_prop = properties.get("Google Place ID", {})
            google_place_id = google_place_id_prop.get("rich_text", [{}])[0].get("plain_text", "")
            
            google_places_data = None
            if google_place_id:
                google_places_data = GooglePlacesData(
                    place_id=google_place_id,
                    name=name
                )
            
            return Restaurant(
                id=page["id"],
                name=name,
                location=location,
                cuisine_types=cuisine_types,
                price_range=price_range,
                vibes=vibes,
                personal_rating=rating,
                notes=notes or None,
                date_visited=date_visited,
                revisit=revisit,
                is_wishlist=is_wishlist,
                google_places_data=google_places_data,
                notion_page_id=page["id"]
            )
            
        except Exception as e:
            logger.error(f"Failed to parse Notion page to restaurant: {e}")
            return None
    
    def _build_notion_filter(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Build Notion filter from filter dictionary."""
        # This is a simplified implementation
        # You can expand this based on your filtering needs
        notion_filter = {}
        
        if "cuisine" in filters:
            notion_filter = {
                "property": "Cuisine",
                "multi_select": {"contains": filters["cuisine"]}
            }
        
        if "city" in filters:
            notion_filter = {
                "property": "City",
                "rich_text": {"equals": filters["city"]}
            }
        
        if "min_rating" in filters:
            notion_filter = {
                "property": "Rating",
                "number": {"greater_than_or_equal_to": filters["min_rating"]}
            }
        
        return notion_filter