"""Data models for the Picky MCP Server."""

from typing import Dict, List, Optional, Union, Any
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class CuisineType(str, Enum):
    """Cuisine type enumeration."""
    AMERICAN = "American"
    ITALIAN = "Italian"
    JAPANESE = "Japanese"
    CHINESE = "Chinese"
    MEXICAN = "Mexican"
    INDIAN = "Indian"
    FRENCH = "French"
    THAI = "Thai"
    MEDITERRANEAN = "Mediterranean"
    SEAFOOD = "Seafood"
    STEAKHOUSE = "Steakhouse"
    PIZZA = "Pizza"
    SUSHI = "Sushi"
    BARBECUE = "Barbecue"
    VEGETARIAN = "Vegetarian"
    VEGAN = "Vegan"
    FAST_FOOD = "Fast Food"
    CAFE = "Cafe"
    BAKERY = "Bakery"
    OTHER = "Other"


class PriceRange(str, Enum):
    """Price range enumeration."""
    BUDGET = "$"
    MODERATE = "$$"
    EXPENSIVE = "$$$"
    VERY_EXPENSIVE = "$$$$"


class VibeType(str, Enum):
    """Restaurant vibe/atmosphere enumeration."""
    CASUAL = "casual"
    ROMANTIC = "romantic"
    FAMILY_FRIENDLY = "family-friendly"
    FINE_DINING = "fine dining"
    TRENDY = "trendy"
    COZY = "cozy"
    LIVELY = "lively"
    QUIET = "quiet"
    OUTDOOR = "outdoor"
    SPORTS_BAR = "sports bar"
    DATE_NIGHT = "date night"
    BUSINESS = "business"
    BRUNCH = "brunch"
    LATE_NIGHT = "late night"
    COUNTER_SERVICE = "counter service"


class OccasionType(str, Enum):
    """Dining occasion enumeration."""
    CASUAL_DINING = "casual dining"
    DATE_NIGHT = "date night"
    BUSINESS_LUNCH = "business lunch"
    FAMILY_DINNER = "family dinner"
    CELEBRATION = "celebration"
    QUICK_BITE = "quick bite"
    WEEKEND_BRUNCH = "weekend brunch"
    HAPPY_HOUR = "happy hour"
    LATE_NIGHT = "late night"
    TAKEOUT = "takeout"


class Location(BaseModel):
    """Geographic location model."""
    address: Optional[str] = None
    city: str
    state: Optional[str] = None
    country: Optional[str] = "USA"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    neighborhood: Optional[str] = None
    postal_code: Optional[str] = None


class GooglePlacesData(BaseModel):
    """Google Places API data model."""
    place_id: str
    name: str
    rating: Optional[float] = None
    price_level: Optional[int] = None
    types: List[str] = []
    formatted_address: Optional[str] = None
    phone_number: Optional[str] = None
    website: Optional[str] = None
    opening_hours: Optional[Dict[str, Any]] = None
    photos: List[str] = []
    reviews: List[Dict[str, Any]] = []


class Restaurant(BaseModel):
    """Restaurant model."""
    id: Optional[str] = None
    name: str
    location: Location
    cuisine_types: List[CuisineType] = []
    price_range: Optional[PriceRange] = None
    vibes: List[VibeType] = []
    personal_rating: Optional[float] = None
    notes: Optional[str] = None
    date_visited: Optional[datetime] = None
    revisit: Optional[bool] = None
    is_wishlist: bool = False
    google_places_data: Optional[GooglePlacesData] = None
    notion_page_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class UserPreferences(BaseModel):
    """User dining preferences model."""
    favorite_cuisines: List[CuisineType] = []
    preferred_price_range: Optional[PriceRange] = None
    preferred_vibes: List[VibeType] = []
    dietary_restrictions: List[str] = []
    max_travel_distance_km: float = 25.0
    preferred_occasions: List[OccasionType] = []
    location_preferences: List[Location] = []


class UserProfile(BaseModel):
    """User profile model."""
    user_id: str
    preferences: UserPreferences
    dining_personality: Optional[str] = None
    total_restaurants: int = 0
    average_rating: Optional[float] = None
    most_common_cuisine: Optional[CuisineType] = None
    most_common_price_range: Optional[PriceRange] = None
    frequent_locations: List[Location] = []
    recent_visits: List[str] = []  # Restaurant IDs
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class RecommendationContext(BaseModel):
    """Context for generating recommendations."""
    user_id: str
    location: Location
    occasion: OccasionType = OccasionType.CASUAL_DINING
    max_distance_km: float = 25.0
    max_results: int = 10
    cuisine_preferences: List[CuisineType] = []
    price_range: Optional[PriceRange] = None
    vibe_preferences: List[VibeType] = []
    exclude_visited: bool = False
    include_wishlist: bool = True


class Recommendation(BaseModel):
    """Restaurant recommendation model."""
    restaurant: Restaurant
    score: float = Field(ge=0.0, le=1.0)
    reasoning: str
    distance_km: Optional[float] = None
    match_factors: Dict[str, float] = {}
    context: Optional[RecommendationContext] = None
    generated_at: datetime = Field(default_factory=datetime.now)


class NotionDatabaseSchema(BaseModel):
    """Notion database schema configuration."""
    database_id: str
    properties: Dict[str, Any] = {
        "Name": {"type": "title"},
        "Rating": {"type": "number"},
        "Cuisine": {"type": "multi_select"},
        "Location": {"type": "rich_text"},
        "Date Visited": {"type": "date"},
        "Notes": {"type": "rich_text"},
        "Google Place ID": {"type": "rich_text"},
        "Price Range": {"type": "select"},
        "Vibes": {"type": "multi_select"},
        "Revisit": {"type": "checkbox"},
        "Wishlist": {"type": "checkbox"},
        "City": {"type": "rich_text"},
        "State": {"type": "rich_text"},
    }


class RecommendationSession(BaseModel):
    """Interactive recommendation session model."""
    session_id: str
    user_id: str
    context: RecommendationContext
    recommendations: List[Recommendation] = []
    feedback: Dict[str, Any] = {}
    learned_preferences: UserPreferences = Field(default_factory=UserPreferences)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class SessionFeedback(BaseModel):
    """User feedback for recommendation sessions."""
    session_id: str
    liked_restaurants: List[str] = []  # Restaurant IDs
    disliked_restaurants: List[str] = []  # Restaurant IDs
    cuisine_feedback: Dict[CuisineType, float] = {}
    vibe_feedback: Dict[VibeType, float] = {}
    price_feedback: Dict[PriceRange, float] = {}
    additional_notes: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class SystemStatus(BaseModel):
    """System status model."""
    notion_connected: bool
    google_maps_connected: bool
    total_restaurants: int
    total_users: int
    last_sync: Optional[datetime] = None
    version: str = "0.1.0"
    uptime: Optional[str] = None