"""Google Maps API client for restaurant data enrichment."""

import logging
from typing import Dict, List, Optional, Any, Tuple
import googlemaps
from googlemaps.exceptions import ApiError

from .models import (
    Restaurant, Location, GooglePlacesData, CuisineType, PriceRange
)
from .config import settings

logger = logging.getLogger(__name__)


class GoogleMapsClient:
    """Manages Google Maps API interactions for restaurant data enrichment."""
    
    def __init__(self, api_key: str = None):
        """Initialize Google Maps client."""
        self.api_key = api_key or settings.google_maps_api_key
        self.client = googlemaps.Client(key=self.api_key)
    
    def test_connection(self) -> Dict[str, Any]:
        """Test Google Maps API connection."""
        try:
            # Test with a simple geocoding request
            result = self.client.geocode("New York, NY")
            return {
                "success": True,
                "message": "Google Maps API connection successful",
                "test_result": len(result) > 0
            }
        except ApiError as e:
            logger.error(f"Google Maps API connection test failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def search_restaurants(
        self,
        query: str,
        location: Tuple[float, float],
        radius: int = 5000,
        restaurant_type: str = "restaurant"
    ) -> List[Dict[str, Any]]:
        """Search for restaurants near a location."""
        try:
            # Use Places API to search for restaurants
            places_result = self.client.places_nearby(
                location=location,
                radius=radius,
                type=restaurant_type,
                keyword=query
            )
            
            restaurants = []
            for place in places_result.get("results", []):
                try:
                    restaurant_data = await self._parse_place_to_restaurant_data(place)
                    if restaurant_data:
                        restaurants.append(restaurant_data)
                except Exception as e:
                    logger.warning(f"Failed to parse place data: {e}")
                    continue
            
            return restaurants
        except ApiError as e:
            logger.error(f"Failed to search restaurants: {e}")
            return []
    
    async def find_restaurant_by_name(
        self,
        name: str,
        location: Tuple[float, float],
        radius: int = 10000
    ) -> Optional[Dict[str, Any]]:
        """Find a specific restaurant by name and location."""
        try:
            # Use text search for more precise results
            places_result = self.client.places(
                query=f"{name} restaurant",
                location=location,
                radius=radius,
                type="restaurant"
            )
            
            for place in places_result.get("results", []):
                if name.lower() in place.get("name", "").lower():
                    return await self._parse_place_to_restaurant_data(place)
            
            return None
        except ApiError as e:
            logger.error(f"Failed to find restaurant by name: {e}")
            return None
    
    async def get_place_details(self, place_id: str) -> Optional[GooglePlacesData]:
        """Get detailed information about a place."""
        try:
            details = self.client.place(
                place_id=place_id,
                fields=[
                    "name", "rating", "price_level", "types",
                    "formatted_address", "formatted_phone_number",
                    "website", "opening_hours", "photos", "reviews",
                    "geometry"
                ]
            )
            
            result = details.get("result", {})
            if not result:
                return None
            
            return GooglePlacesData(
                place_id=place_id,
                name=result.get("name", ""),
                rating=result.get("rating"),
                price_level=result.get("price_level"),
                types=result.get("types", []),
                formatted_address=result.get("formatted_address"),
                phone_number=result.get("formatted_phone_number"),
                website=result.get("website"),
                opening_hours=result.get("opening_hours"),
                photos=[photo.get("photo_reference", "") for photo in result.get("photos", [])],
                reviews=result.get("reviews", [])
            )
        except ApiError as e:
            logger.error(f"Failed to get place details: {e}")
            return None
    
    async def find_similar_restaurants(
        self,
        place_id: str,
        radius: int = 5000
    ) -> List[Dict[str, Any]]:
        """Find restaurants similar to a given place."""
        try:
            # First get the details of the original place
            place_details = await self.get_place_details(place_id)
            if not place_details:
                return []
            
            # Get the location of the original place
            details = self.client.place(place_id=place_id, fields=["geometry"])
            location_data = details.get("result", {}).get("geometry", {}).get("location", {})
            
            if not location_data:
                return []
            
            location = (location_data["lat"], location_data["lng"])
            
            # Search for similar restaurants based on cuisine types
            similar_restaurants = []
            cuisine_types = self._extract_cuisine_from_types(place_details.types)
            
            for cuisine in cuisine_types:
                restaurants = await self.search_restaurants(
                    query=f"{cuisine} restaurant",
                    location=location,
                    radius=radius
                )
                similar_restaurants.extend(restaurants)
            
            # Remove duplicates and the original restaurant
            unique_restaurants = []
            seen_place_ids = {place_id}
            
            for restaurant in similar_restaurants:
                if restaurant.get("place_id") not in seen_place_ids:
                    unique_restaurants.append(restaurant)
                    seen_place_ids.add(restaurant.get("place_id"))
            
            return unique_restaurants[:10]  # Limit to top 10
        except ApiError as e:
            logger.error(f"Failed to find similar restaurants: {e}")
            return []
    
    async def enrich_restaurant_data(self, restaurant: Restaurant) -> Restaurant:
        """Enrich restaurant data with Google Maps information."""
        try:
            # If we already have Google Places data, update it
            if restaurant.google_places_data and restaurant.google_places_data.place_id:
                place_details = await self.get_place_details(restaurant.google_places_data.place_id)
                if place_details:
                    restaurant.google_places_data = place_details
            else:
                # Search for the restaurant by name and location
                if restaurant.location.latitude and restaurant.location.longitude:
                    location = (restaurant.location.latitude, restaurant.location.longitude)
                else:
                    # Geocode the address
                    location = await self._geocode_address(restaurant.location)
                
                if location:
                    restaurant_data = await self.find_restaurant_by_name(
                        restaurant.name,
                        location
                    )
                    
                    if restaurant_data:
                        restaurant.google_places_data = GooglePlacesData(
                            place_id=restaurant_data["place_id"],
                            name=restaurant_data["name"],
                            rating=restaurant_data.get("rating"),
                            price_level=restaurant_data.get("price_level"),
                            types=restaurant_data.get("types", []),
                            formatted_address=restaurant_data.get("formatted_address")
                        )
            
            # Update location coordinates if we have them
            if restaurant.google_places_data:
                details = self.client.place(
                    place_id=restaurant.google_places_data.place_id,
                    fields=["geometry"]
                )
                geometry = details.get("result", {}).get("geometry", {})
                if geometry.get("location"):
                    restaurant.location.latitude = geometry["location"]["lat"]
                    restaurant.location.longitude = geometry["location"]["lng"]
            
            return restaurant
        except Exception as e:
            logger.error(f"Failed to enrich restaurant data: {e}")
            return restaurant
    
    async def get_restaurant_recommendations_near_location(
        self,
        location: Tuple[float, float],
        radius: int = 5000,
        cuisine_type: str = None,
        min_rating: float = 4.0,
        price_level: int = None
    ) -> List[Dict[str, Any]]:
        """Get restaurant recommendations near a location."""
        try:
            query = f"{cuisine_type} restaurant" if cuisine_type else "restaurant"
            
            places_result = self.client.places_nearby(
                location=location,
                radius=radius,
                type="restaurant",
                keyword=query
            )
            
            restaurants = []
            for place in places_result.get("results", []):
                try:
                    # Filter by rating if specified
                    if min_rating and place.get("rating", 0) < min_rating:
                        continue
                    
                    # Filter by price level if specified
                    if price_level and place.get("price_level") != price_level:
                        continue
                    
                    restaurant_data = await self._parse_place_to_restaurant_data(place)
                    if restaurant_data:
                        restaurants.append(restaurant_data)
                except Exception as e:
                    logger.warning(f"Failed to parse place data: {e}")
                    continue
            
            return restaurants
        except ApiError as e:
            logger.error(f"Failed to get recommendations: {e}")
            return []
    
    async def _parse_place_to_restaurant_data(self, place: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse Google Places API place data to restaurant data."""
        try:
            place_id = place.get("place_id")
            if not place_id:
                return None
            
            name = place.get("name", "")
            if not name:
                return None
            
            # Extract location
            geometry = place.get("geometry", {})
            location_data = geometry.get("location", {})
            
            # Parse address
            address = place.get("vicinity") or place.get("formatted_address", "")
            
            # Parse cuisine types from Google Places types
            types = place.get("types", [])
            cuisine_types = self._extract_cuisine_from_types(types)
            
            # Parse price range
            price_level = place.get("price_level")
            price_range = self._map_price_level_to_range(price_level)
            
            return {
                "place_id": place_id,
                "name": name,
                "rating": place.get("rating"),
                "price_level": price_level,
                "price_range": price_range,
                "types": types,
                "cuisine_types": cuisine_types,
                "formatted_address": address,
                "location": {
                    "latitude": location_data.get("lat"),
                    "longitude": location_data.get("lng")
                },
                "opening_hours": place.get("opening_hours"),
                "photos": place.get("photos", [])
            }
        except Exception as e:
            logger.error(f"Failed to parse place data: {e}")
            return None
    
    def _extract_cuisine_from_types(self, types: List[str]) -> List[CuisineType]:
        """Extract cuisine types from Google Places types."""
        cuisine_mapping = {
            "italian_restaurant": CuisineType.ITALIAN,
            "chinese_restaurant": CuisineType.CHINESE,
            "japanese_restaurant": CuisineType.JAPANESE,
            "mexican_restaurant": CuisineType.MEXICAN,
            "indian_restaurant": CuisineType.INDIAN,
            "french_restaurant": CuisineType.FRENCH,
            "thai_restaurant": CuisineType.THAI,
            "mediterranean_restaurant": CuisineType.MEDITERRANEAN,
            "american_restaurant": CuisineType.AMERICAN,
            "seafood_restaurant": CuisineType.SEAFOOD,
            "steak_house": CuisineType.STEAKHOUSE,
            "pizza_restaurant": CuisineType.PIZZA,
            "sushi_restaurant": CuisineType.SUSHI,
            "barbecue_restaurant": CuisineType.BARBECUE,
            "vegetarian_restaurant": CuisineType.VEGETARIAN,
            "meal_takeaway": CuisineType.FAST_FOOD,
            "fast_food_restaurant": CuisineType.FAST_FOOD,
            "cafe": CuisineType.CAFE,
            "bakery": CuisineType.BAKERY,
        }
        
        cuisines = []
        for place_type in types:
            if place_type in cuisine_mapping:
                cuisines.append(cuisine_mapping[place_type])
        
        return cuisines if cuisines else [CuisineType.OTHER]
    
    def _map_price_level_to_range(self, price_level: Optional[int]) -> Optional[PriceRange]:
        """Map Google Places price level to our price range enum."""
        if price_level is None:
            return None
        
        mapping = {
            0: PriceRange.BUDGET,
            1: PriceRange.BUDGET,
            2: PriceRange.MODERATE,
            3: PriceRange.EXPENSIVE,
            4: PriceRange.VERY_EXPENSIVE,
        }
        
        return mapping.get(price_level)
    
    async def _geocode_address(self, location: Location) -> Optional[Tuple[float, float]]:
        """Geocode an address to get coordinates."""
        try:
            address_parts = []
            if location.address:
                address_parts.append(location.address)
            if location.city:
                address_parts.append(location.city)
            if location.state:
                address_parts.append(location.state)
            if location.country:
                address_parts.append(location.country)
            
            address = ", ".join(address_parts)
            if not address:
                return None
            
            geocode_result = self.client.geocode(address)
            if geocode_result:
                location_data = geocode_result[0]["geometry"]["location"]
                return (location_data["lat"], location_data["lng"])
            
            return None
        except Exception as e:
            logger.error(f"Failed to geocode address: {e}")
            return None