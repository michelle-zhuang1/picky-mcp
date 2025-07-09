"""Restaurant manager with recommendation logic."""

import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import asyncio
from collections import defaultdict, Counter
import math

from .models import (
    Restaurant, UserProfile, UserPreferences, Recommendation,
    RecommendationContext, Location, CuisineType, PriceRange,
    VibeType, OccasionType, RecommendationSession, SessionFeedback
)
from .notion_client import NotionManager
from .maps_client import GoogleMapsClient
from .config import settings

logger = logging.getLogger(__name__)


class RestaurantManager:
    """Manages restaurant data and provides intelligent recommendations."""
    
    def __init__(self, notion_client: NotionManager, maps_client: GoogleMapsClient):
        """Initialize restaurant manager."""
        self.notion = notion_client
        self.maps = maps_client
        self._user_profiles: Dict[str, UserProfile] = {}
        self._recommendation_sessions: Dict[str, RecommendationSession] = {}
    
    async def get_recommendations(
        self,
        user_id: str,
        context: RecommendationContext
    ) -> List[Recommendation]:
        """Generate personalized restaurant recommendations."""
        try:
            # Get user profile
            user_profile = await self._get_or_create_user_profile(user_id)
            
            # Get restaurants from Notion
            notion_restaurants = await self.notion.get_all_restaurants()
            
            # Get additional restaurants from Google Maps if location is provided
            google_restaurants = []
            if context.location.latitude and context.location.longitude:
                google_restaurants = await self._get_google_restaurants(context)
            
            # Combine and filter restaurants
            all_restaurants = self._combine_and_filter_restaurants(
                notion_restaurants, google_restaurants, user_profile, context
            )
            
            # Generate recommendations
            recommendations = []
            for restaurant in all_restaurants:
                score = await self._calculate_recommendation_score(
                    restaurant, user_profile, context
                )
                
                if score > 0.1:  # Minimum threshold
                    reasoning = self._generate_reasoning(
                        restaurant, user_profile, context, score
                    )
                    
                    distance = self._calculate_distance(
                        restaurant.location, context.location
                    )
                    
                    recommendation = Recommendation(
                        restaurant=restaurant,
                        score=score,
                        reasoning=reasoning,
                        distance_km=distance,
                        context=context
                    )
                    recommendations.append(recommendation)
            
            # Sort by score and return top results
            recommendations.sort(key=lambda x: x.score, reverse=True)
            return recommendations[:context.max_results]
            
        except Exception as e:
            logger.error(f"Failed to generate recommendations: {e}")
            return []
    
    async def add_restaurant_visit(
        self,
        user_id: str,
        restaurant_name: str,
        rating: float,
        notes: str = None,
        date: datetime = None
    ) -> Dict[str, Any]:
        """Add a new restaurant visit to Notion database."""
        try:
            # Check if restaurant already exists
            existing_restaurant = await self.notion.get_restaurant_by_name(restaurant_name)
            
            if existing_restaurant:
                # Update existing restaurant
                existing_restaurant.personal_rating = rating
                existing_restaurant.notes = notes
                existing_restaurant.date_visited = date or datetime.now()
                
                result = await self.notion.update_restaurant(
                    existing_restaurant.notion_page_id,
                    existing_restaurant
                )
            else:
                # Create new restaurant entry
                # This would need location data - simplified for now
                restaurant = Restaurant(
                    name=restaurant_name,
                    location=Location(city="Unknown"),  # Would need to be provided
                    personal_rating=rating,
                    notes=notes,
                    date_visited=date or datetime.now()
                )
                
                result = await self.notion.add_restaurant(restaurant)
            
            # Update user profile
            await self._update_user_profile(user_id)
            
            return {
                "success": True,
                "message": f"Added visit to {restaurant_name} with rating {rating}",
                "restaurant_name": restaurant_name,
                "rating": rating
            }
            
        except Exception as e:
            logger.error(f"Failed to add restaurant visit: {e}")
            return {"success": False, "error": str(e)}
    
    async def analyze_dining_patterns(self, user_id: str) -> Dict[str, Any]:
        """Analyze user's dining patterns and preferences."""
        try:
            user_profile = await self._get_or_create_user_profile(user_id)
            restaurants = await self.notion.get_all_restaurants()
            
            # Filter restaurants with ratings (actual visits)
            rated_restaurants = [r for r in restaurants if r.personal_rating is not None]
            
            analysis = {
                "total_restaurants": len(restaurants),
                "total_visits": len(rated_restaurants),
                "average_rating": user_profile.average_rating,
                "dining_personality": user_profile.dining_personality,
                "favorite_cuisines": self._analyze_cuisine_preferences(rated_restaurants),
                "price_comfort_zone": self._analyze_price_preferences(rated_restaurants),
                "preferred_vibes": self._analyze_vibe_preferences(rated_restaurants),
                "location_patterns": self._analyze_location_patterns(rated_restaurants),
                "recent_trends": self._analyze_recent_trends(rated_restaurants),
                "recommendations_insights": self._generate_insights(user_profile, rated_restaurants)
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to analyze dining patterns: {e}")
            return {"error": str(e)}
    
    async def find_similar_restaurants(
        self,
        restaurant_name: str,
        user_id: str,
        max_results: int = 5
    ) -> List[Recommendation]:
        """Find restaurants similar to a given restaurant."""
        try:
            # Find the reference restaurant
            reference_restaurant = await self.notion.get_restaurant_by_name(restaurant_name)
            if not reference_restaurant:
                return []
            
            # Get user profile
            user_profile = await self._get_or_create_user_profile(user_id)
            
            # Get all restaurants
            all_restaurants = await self.notion.get_all_restaurants()
            
            # Find similar restaurants
            similar_restaurants = []
            for restaurant in all_restaurants:
                if restaurant.name == restaurant_name:
                    continue  # Skip the reference restaurant
                
                similarity_score = self._calculate_similarity(
                    reference_restaurant, restaurant
                )
                
                if similarity_score > 0.3:  # Minimum similarity threshold
                    reasoning = f"Similar to {restaurant_name} - shared cuisine types and vibes"
                    
                    recommendation = Recommendation(
                        restaurant=restaurant,
                        score=similarity_score,
                        reasoning=reasoning
                    )
                    similar_restaurants.append(recommendation)
            
            # Sort by similarity score
            similar_restaurants.sort(key=lambda x: x.score, reverse=True)
            return similar_restaurants[:max_results]
            
        except Exception as e:
            logger.error(f"Failed to find similar restaurants: {e}")
            return []
    
    async def enrich_restaurant_database(self) -> Dict[str, Any]:
        """Automatically enrich all restaurants with Google Maps data."""
        try:
            restaurants = await self.notion.get_all_restaurants()
            enriched_count = 0
            failed_count = 0
            
            for restaurant in restaurants:
                try:
                    # Skip if already enriched
                    if restaurant.google_places_data and restaurant.google_places_data.place_id:
                        continue
                    
                    # Enrich with Google Maps data
                    enriched_restaurant = await self.maps.enrich_restaurant_data(restaurant)
                    
                    # Update in Notion if enrichment was successful
                    if enriched_restaurant.google_places_data:
                        await self.notion.update_restaurant(
                            restaurant.notion_page_id,
                            enriched_restaurant
                        )
                        enriched_count += 1
                    
                    # Add small delay to avoid rate limiting
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    logger.warning(f"Failed to enrich restaurant {restaurant.name}: {e}")
                    failed_count += 1
                    continue
            
            return {
                "success": True,
                "total_restaurants": len(restaurants),
                "enriched_count": enriched_count,
                "failed_count": failed_count,
                "message": f"Enriched {enriched_count} restaurants with Google Maps data"
            }
            
        except Exception as e:
            logger.error(f"Failed to enrich restaurant database: {e}")
            return {"success": False, "error": str(e)}
    
    async def start_interactive_session(
        self,
        user_id: str,
        context: RecommendationContext
    ) -> RecommendationSession:
        """Start an interactive recommendation session."""
        session_id = f"{user_id}_{datetime.now().isoformat()}"
        
        session = RecommendationSession(
            session_id=session_id,
            user_id=user_id,
            context=context
        )
        
        # Generate initial recommendations
        recommendations = await self.get_recommendations(user_id, context)
        session.recommendations = recommendations
        
        # Store session
        self._recommendation_sessions[session_id] = session
        
        return session
    
    async def process_session_feedback(
        self,
        session_id: str,
        feedback: SessionFeedback
    ) -> Dict[str, Any]:
        """Process user feedback and update session preferences."""
        try:
            session = self._recommendation_sessions.get(session_id)
            if not session:
                return {"success": False, "error": "Session not found"}
            
            # Update learned preferences based on feedback
            session.learned_preferences = self._update_preferences_from_feedback(
                session.learned_preferences, feedback
            )
            
            # Store feedback
            session.feedback[feedback.timestamp.isoformat()] = feedback
            session.updated_at = datetime.now()
            
            return {
                "success": True,
                "message": "Feedback processed successfully",
                "learned_preferences": session.learned_preferences
            }
            
        except Exception as e:
            logger.error(f"Failed to process session feedback: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_session_recommendations(
        self,
        session_id: str
    ) -> List[Recommendation]:
        """Get refined recommendations based on session feedback."""
        try:
            session = self._recommendation_sessions.get(session_id)
            if not session:
                return []
            
            # Update context with learned preferences
            updated_context = self._apply_learned_preferences(
                session.context, session.learned_preferences
            )
            
            # Generate new recommendations
            recommendations = await self.get_recommendations(
                session.user_id, updated_context
            )
            
            # Filter out previously disliked restaurants
            filtered_recommendations = []
            for feedback in session.feedback.values():
                disliked_ids = set(feedback.disliked_restaurants)
                
                for rec in recommendations:
                    if rec.restaurant.id not in disliked_ids:
                        filtered_recommendations.append(rec)
            
            return filtered_recommendations
            
        except Exception as e:
            logger.error(f"Failed to get session recommendations: {e}")
            return []
    
    async def generate_dining_profile(self, user_id: str) -> str:
        """Generate a comprehensive dining profile summary."""
        try:
            analysis = await self.analyze_dining_patterns(user_id)
            
            profile_parts = [
                f"🍽️ **Dining Profile for {user_id}**\\n",
                f"📊 **Statistics:**",
                f"• Total restaurants: {analysis.get('total_restaurants', 0)}",
                f"• Total visits: {analysis.get('total_visits', 0)}",
                f"• Average rating: {analysis.get('average_rating', 'N/A')}",
                f"• Dining personality: {analysis.get('dining_personality', 'Unknown')}\\n",
                
                f"🍜 **Favorite Cuisines:**"
            ]
            
            favorite_cuisines = analysis.get('favorite_cuisines', [])[:5]
            for cuisine in favorite_cuisines:
                profile_parts.append(f"• {cuisine.get('name', 'Unknown')}: {cuisine.get('count', 0)} visits")
            
            profile_parts.extend([
                f"\\n💰 **Price Comfort Zone:** {analysis.get('price_comfort_zone', 'Unknown')}",
                f"\\n🌟 **Preferred Vibes:**"
            ])
            
            preferred_vibes = analysis.get('preferred_vibes', [])[:3]
            for vibe in preferred_vibes:
                profile_parts.append(f"• {vibe.get('name', 'Unknown')}")
            
            insights = analysis.get('recommendations_insights', [])
            if insights:
                profile_parts.append("\\n💡 **Insights:**")
                for insight in insights[:3]:
                    profile_parts.append(f"• {insight}")
            
            return "\\n".join(profile_parts)
            
        except Exception as e:
            logger.error(f"Failed to generate dining profile: {e}")
            return f"Error generating profile: {str(e)}"
    
    # Private helper methods
    
    async def _get_or_create_user_profile(self, user_id: str) -> UserProfile:
        """Get or create user profile."""
        if user_id not in self._user_profiles:
            await self._update_user_profile(user_id)
        return self._user_profiles[user_id]
    
    async def _update_user_profile(self, user_id: str) -> None:
        """Update user profile based on Notion data."""
        try:
            restaurants = await self.notion.get_all_restaurants()
            rated_restaurants = [r for r in restaurants if r.personal_rating is not None]
            
            # Calculate basic statistics
            total_restaurants = len(restaurants)
            average_rating = sum(r.personal_rating for r in rated_restaurants) / len(rated_restaurants) if rated_restaurants else None
            
            # Analyze preferences
            preferences = self._analyze_preferences(rated_restaurants)
            
            # Determine dining personality
            personality = self._determine_dining_personality(rated_restaurants)
            
            # Create or update profile
            profile = UserProfile(
                user_id=user_id,
                preferences=preferences,
                dining_personality=personality,
                total_restaurants=total_restaurants,
                average_rating=average_rating,
                most_common_cuisine=self._get_most_common_cuisine(rated_restaurants),
                most_common_price_range=self._get_most_common_price_range(rated_restaurants),
                frequent_locations=self._get_frequent_locations(rated_restaurants),
                recent_visits=[r.id for r in rated_restaurants[-10:]]
            )
            
            self._user_profiles[user_id] = profile
            
        except Exception as e:
            logger.error(f"Failed to update user profile: {e}")
    
    def _analyze_preferences(self, restaurants: List[Restaurant]) -> UserPreferences:
        """Analyze user preferences from restaurant data."""
        preferences = UserPreferences()
        
        if not restaurants:
            return preferences
        
        # Analyze cuisine preferences
        cuisine_ratings = defaultdict(list)
        for restaurant in restaurants:
            if restaurant.personal_rating:
                for cuisine in restaurant.cuisine_types:
                    cuisine_ratings[cuisine].append(restaurant.personal_rating)
        
        # Get cuisines with average rating >= 4.0
        favorite_cuisines = []
        for cuisine, ratings in cuisine_ratings.items():
            avg_rating = sum(ratings) / len(ratings)
            if avg_rating >= 4.0 and len(ratings) >= 2:
                favorite_cuisines.append(cuisine)
        
        preferences.favorite_cuisines = favorite_cuisines
        
        # Analyze price preferences
        price_ratings = defaultdict(list)
        for restaurant in restaurants:
            if restaurant.personal_rating and restaurant.price_range:
                price_ratings[restaurant.price_range].append(restaurant.personal_rating)
        
        # Get most frequently used price range with good ratings
        best_price_range = None
        best_score = 0
        for price_range, ratings in price_ratings.items():
            if ratings:
                avg_rating = sum(ratings) / len(ratings)
                frequency = len(ratings)
                score = avg_rating * frequency
                if score > best_score:
                    best_score = score
                    best_price_range = price_range
        
        preferences.preferred_price_range = best_price_range
        
        # Analyze vibe preferences
        vibe_ratings = defaultdict(list)
        for restaurant in restaurants:
            if restaurant.personal_rating:
                for vibe in restaurant.vibes:
                    vibe_ratings[vibe].append(restaurant.personal_rating)
        
        preferred_vibes = []
        for vibe, ratings in vibe_ratings.items():
            avg_rating = sum(ratings) / len(ratings)
            if avg_rating >= 4.0 and len(ratings) >= 2:
                preferred_vibes.append(vibe)
        
        preferences.preferred_vibes = preferred_vibes
        
        return preferences
    
    def _determine_dining_personality(self, restaurants: List[Restaurant]) -> str:
        """Determine dining personality based on restaurant patterns."""
        if not restaurants:
            return "Unknown"
        
        # Analyze patterns
        cuisine_diversity = len(set(c for r in restaurants for c in r.cuisine_types))
        avg_rating = sum(r.personal_rating for r in restaurants if r.personal_rating) / len([r for r in restaurants if r.personal_rating])
        
        price_ranges = [r.price_range for r in restaurants if r.price_range]
        expensive_count = sum(1 for p in price_ranges if p in [PriceRange.EXPENSIVE, PriceRange.VERY_EXPENSIVE])
        
        fine_dining_count = sum(1 for r in restaurants if VibeType.FINE_DINING in r.vibes)
        
        # Determine personality
        if cuisine_diversity > 10 and avg_rating > 4.0:
            return "Adventurous Eater"
        elif fine_dining_count > len(restaurants) * 0.3:
            return "Fine Dining Enthusiast"
        elif expensive_count > len(restaurants) * 0.5:
            return "Upscale Diner"
        elif avg_rating > 4.2:
            return "Discerning Foodie"
        else:
            return "Casual Explorer"
    
    async def _get_google_restaurants(self, context: RecommendationContext) -> List[Restaurant]:
        """Get additional restaurants from Google Maps."""
        try:
            location = (context.location.latitude, context.location.longitude)
            
            # Search for restaurants based on preferences
            all_restaurants = []
            
            # Search by cuisine preferences
            for cuisine in context.cuisine_preferences:
                restaurants_data = await self.maps.search_restaurants(
                    query=f"{cuisine.value} restaurant",
                    location=location,
                    radius=int(context.max_distance_km * 1000)
                )
                
                for data in restaurants_data:
                    restaurant = self._convert_google_data_to_restaurant(data)
                    if restaurant:
                        all_restaurants.append(restaurant)
            
            # If no specific cuisine preferences, search generally
            if not context.cuisine_preferences:
                restaurants_data = await self.maps.search_restaurants(
                    query="restaurant",
                    location=location,
                    radius=int(context.max_distance_km * 1000)
                )
                
                for data in restaurants_data:
                    restaurant = self._convert_google_data_to_restaurant(data)
                    if restaurant:
                        all_restaurants.append(restaurant)
            
            return all_restaurants
            
        except Exception as e:
            logger.error(f"Failed to get Google restaurants: {e}")
            return []
    
    def _convert_google_data_to_restaurant(self, data: Dict[str, Any]) -> Optional[Restaurant]:
        """Convert Google Maps data to Restaurant model."""
        try:
            location_data = data.get("location", {})
            
            location = Location(
                address=data.get("formatted_address", ""),
                city="Unknown",  # Would need to parse from address
                latitude=location_data.get("latitude"),
                longitude=location_data.get("longitude")
            )
            
            cuisine_types = data.get("cuisine_types", [])
            price_range = data.get("price_range")
            
            restaurant = Restaurant(
                id=data.get("place_id"),
                name=data.get("name", ""),
                location=location,
                cuisine_types=cuisine_types,
                price_range=price_range,
                is_wishlist=True  # Mark Google results as wishlist items
            )
            
            return restaurant
            
        except Exception as e:
            logger.error(f"Failed to convert Google data to restaurant: {e}")
            return None
    
    def _combine_and_filter_restaurants(
        self,
        notion_restaurants: List[Restaurant],
        google_restaurants: List[Restaurant],
        user_profile: UserProfile,
        context: RecommendationContext
    ) -> List[Restaurant]:
        """Combine and filter restaurants based on context."""
        all_restaurants = notion_restaurants + google_restaurants
        
        # Remove duplicates based on name and location
        unique_restaurants = []
        seen = set()
        
        for restaurant in all_restaurants:
            key = (restaurant.name.lower(), restaurant.location.city.lower())
            if key not in seen:
                seen.add(key)
                unique_restaurants.append(restaurant)
        
        # Filter based on context
        filtered_restaurants = []
        
        for restaurant in unique_restaurants:
            # Skip if exclude_visited is True and restaurant has been visited
            if context.exclude_visited and restaurant.personal_rating is not None:
                continue
            
            # Include wishlist items if specified
            if context.include_wishlist and restaurant.is_wishlist:
                filtered_restaurants.append(restaurant)
                continue
            
            # Filter by cuisine preferences
            if context.cuisine_preferences:
                if not any(cuisine in restaurant.cuisine_types for cuisine in context.cuisine_preferences):
                    continue
            
            # Filter by price range
            if context.price_range and restaurant.price_range:
                if restaurant.price_range != context.price_range:
                    continue
            
            # Filter by vibe preferences
            if context.vibe_preferences:
                if not any(vibe in restaurant.vibes for vibe in context.vibe_preferences):
                    continue
            
            # Filter by distance
            distance = self._calculate_distance(restaurant.location, context.location)
            if distance and distance > context.max_distance_km:
                continue
            
            filtered_restaurants.append(restaurant)
        
        return filtered_restaurants
    
    async def _calculate_recommendation_score(
        self,
        restaurant: Restaurant,
        user_profile: UserProfile,
        context: RecommendationContext
    ) -> float:
        """Calculate recommendation score for a restaurant."""
        score = 0.0
        
        # Base score
        base_score = 0.5
        
        # Cuisine preference match
        cuisine_score = 0.0
        if restaurant.cuisine_types:
            for cuisine in restaurant.cuisine_types:
                if cuisine in user_profile.preferences.favorite_cuisines:
                    cuisine_score += 0.3
            cuisine_score = min(cuisine_score, 0.6)  # Cap at 0.6
        
        # Price range match
        price_score = 0.0
        if (restaurant.price_range and 
            restaurant.price_range == user_profile.preferences.preferred_price_range):
            price_score = 0.2
        
        # Vibe match
        vibe_score = 0.0
        if restaurant.vibes:
            for vibe in restaurant.vibes:
                if vibe in user_profile.preferences.preferred_vibes:
                    vibe_score += 0.1
            vibe_score = min(vibe_score, 0.3)  # Cap at 0.3
        
        # Distance penalty
        distance_score = 0.0
        distance = self._calculate_distance(restaurant.location, context.location)
        if distance:
            # Closer restaurants get higher scores
            distance_score = max(0, 0.2 - (distance / context.max_distance_km) * 0.2)
        
        # Google rating bonus
        google_rating_score = 0.0
        if restaurant.google_places_data and restaurant.google_places_data.rating:
            # Higher rated restaurants get bonus
            google_rating_score = min(0.2, (restaurant.google_places_data.rating - 3.0) / 2.0 * 0.2)
        
        # Occasion match
        occasion_score = 0.0
        if context.occasion:
            occasion_score = self._calculate_occasion_match(restaurant, context.occasion)
        
        # Combine scores
        score = base_score + cuisine_score + price_score + vibe_score + distance_score + google_rating_score + occasion_score
        
        return min(score, 1.0)  # Cap at 1.0
    
    def _calculate_occasion_match(self, restaurant: Restaurant, occasion: OccasionType) -> float:
        """Calculate how well a restaurant matches the occasion."""
        occasion_vibe_mapping = {
            OccasionType.DATE_NIGHT: [VibeType.ROMANTIC, VibeType.FINE_DINING],
            OccasionType.BUSINESS_LUNCH: [VibeType.BUSINESS, VibeType.QUIET],
            OccasionType.FAMILY_DINNER: [VibeType.FAMILY_FRIENDLY, VibeType.CASUAL],
            OccasionType.CELEBRATION: [VibeType.FINE_DINING, VibeType.TRENDY],
            OccasionType.QUICK_BITE: [VibeType.CASUAL, VibeType.FAST_FOOD],
            OccasionType.WEEKEND_BRUNCH: [VibeType.BRUNCH, VibeType.CASUAL],
            OccasionType.HAPPY_HOUR: [VibeType.SPORTS_BAR, VibeType.LIVELY],
            OccasionType.LATE_NIGHT: [VibeType.LATE_NIGHT, VibeType.CASUAL]
        }
        
        preferred_vibes = occasion_vibe_mapping.get(occasion, [])
        
        match_score = 0.0
        for vibe in restaurant.vibes:
            if vibe in preferred_vibes:
                match_score += 0.1
        
        return min(match_score, 0.2)  # Cap at 0.2
    
    def _generate_reasoning(
        self,
        restaurant: Restaurant,
        user_profile: UserProfile,
        context: RecommendationContext,
        score: float
    ) -> str:
        """Generate reasoning for recommendation."""
        reasons = []
        
        # Cuisine match
        cuisine_matches = [c for c in restaurant.cuisine_types if c in user_profile.preferences.favorite_cuisines]
        if cuisine_matches:
            reasons.append(f"Matches your favorite cuisines: {', '.join(c.value for c in cuisine_matches)}")
        
        # Price match
        if (restaurant.price_range and 
            restaurant.price_range == user_profile.preferences.preferred_price_range):
            reasons.append(f"Fits your preferred price range ({restaurant.price_range.value})")
        
        # Vibe match
        vibe_matches = [v for v in restaurant.vibes if v in user_profile.preferences.preferred_vibes]
        if vibe_matches:
            reasons.append(f"Matches your preferred vibes: {', '.join(v.value for v in vibe_matches)}")
        
        # Google rating
        if restaurant.google_places_data and restaurant.google_places_data.rating:
            if restaurant.google_places_data.rating >= 4.0:
                reasons.append(f"Highly rated on Google ({restaurant.google_places_data.rating}/5)")
        
        # Distance
        distance = self._calculate_distance(restaurant.location, context.location)
        if distance and distance <= 5:
            reasons.append(f"Conveniently located ({distance:.1f}km away)")
        
        # Occasion
        if context.occasion != OccasionType.CASUAL_DINING:
            reasons.append(f"Good for {context.occasion.value}")
        
        if not reasons:
            reasons.append("Based on your dining preferences")
        
        return "; ".join(reasons)
    
    def _calculate_distance(self, location1: Location, location2: Location) -> Optional[float]:
        """Calculate distance between two locations in kilometers."""
        if not all([location1.latitude, location1.longitude, location2.latitude, location2.longitude]):
            return None
        
        # Haversine formula
        R = 6371  # Earth's radius in km
        
        lat1, lon1 = math.radians(location1.latitude), math.radians(location1.longitude)
        lat2, lon2 = math.radians(location2.latitude), math.radians(location2.longitude)
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        return R * c
    
    def _calculate_similarity(self, restaurant1: Restaurant, restaurant2: Restaurant) -> float:
        """Calculate similarity between two restaurants."""
        similarity = 0.0
        
        # Cuisine similarity
        common_cuisines = set(restaurant1.cuisine_types) & set(restaurant2.cuisine_types)
        if common_cuisines:
            similarity += 0.4
        
        # Price similarity
        if restaurant1.price_range and restaurant2.price_range:
            if restaurant1.price_range == restaurant2.price_range:
                similarity += 0.3
        
        # Vibe similarity
        common_vibes = set(restaurant1.vibes) & set(restaurant2.vibes)
        if common_vibes:
            similarity += 0.3
        
        return similarity
    
    def _analyze_cuisine_preferences(self, restaurants: List[Restaurant]) -> List[Dict[str, Any]]:
        """Analyze cuisine preferences from restaurants."""
        cuisine_counter = Counter()
        cuisine_ratings = defaultdict(list)
        
        for restaurant in restaurants:
            if restaurant.personal_rating:
                for cuisine in restaurant.cuisine_types:
                    cuisine_counter[cuisine] += 1
                    cuisine_ratings[cuisine].append(restaurant.personal_rating)
        
        cuisine_analysis = []
        for cuisine, count in cuisine_counter.most_common():
            avg_rating = sum(cuisine_ratings[cuisine]) / len(cuisine_ratings[cuisine])
            cuisine_analysis.append({
                "name": cuisine.value,
                "count": count,
                "average_rating": round(avg_rating, 2)
            })
        
        return cuisine_analysis
    
    def _analyze_price_preferences(self, restaurants: List[Restaurant]) -> str:
        """Analyze price preferences."""
        price_counter = Counter()
        for restaurant in restaurants:
            if restaurant.price_range:
                price_counter[restaurant.price_range] += 1
        
        if price_counter:
            most_common_price = price_counter.most_common(1)[0][0]
            return most_common_price.value
        
        return "Unknown"
    
    def _analyze_vibe_preferences(self, restaurants: List[Restaurant]) -> List[Dict[str, Any]]:
        """Analyze vibe preferences."""
        vibe_counter = Counter()
        for restaurant in restaurants:
            for vibe in restaurant.vibes:
                vibe_counter[vibe] += 1
        
        vibe_analysis = []
        for vibe, count in vibe_counter.most_common(5):
            vibe_analysis.append({
                "name": vibe.value,
                "count": count
            })
        
        return vibe_analysis
    
    def _analyze_location_patterns(self, restaurants: List[Restaurant]) -> List[Dict[str, Any]]:
        """Analyze location patterns."""
        location_counter = Counter()
        for restaurant in restaurants:
            location_counter[restaurant.location.city] += 1
        
        location_analysis = []
        for city, count in location_counter.most_common(5):
            location_analysis.append({
                "city": city,
                "count": count
            })
        
        return location_analysis
    
    def _analyze_recent_trends(self, restaurants: List[Restaurant]) -> List[str]:
        """Analyze recent dining trends."""
        recent_restaurants = [r for r in restaurants if r.date_visited and r.date_visited > datetime.now() - timedelta(days=30)]
        
        if not recent_restaurants:
            return ["No recent dining activity"]
        
        trends = []
        
        # Recent cuisine trends
        recent_cuisines = Counter()
        for restaurant in recent_restaurants:
            for cuisine in restaurant.cuisine_types:
                recent_cuisines[cuisine] += 1
        
        if recent_cuisines:
            top_cuisine = recent_cuisines.most_common(1)[0][0]
            trends.append(f"Recently favoring {top_cuisine.value} cuisine")
        
        # Recent rating trends
        recent_ratings = [r.personal_rating for r in recent_restaurants if r.personal_rating]
        if recent_ratings:
            avg_recent_rating = sum(recent_ratings) / len(recent_ratings)
            trends.append(f"Recent average rating: {avg_recent_rating:.1f}")
        
        return trends
    
    def _generate_insights(self, user_profile: UserProfile, restaurants: List[Restaurant]) -> List[str]:
        """Generate insights about dining patterns."""
        insights = []
        
        if user_profile.average_rating and user_profile.average_rating > 4.0:
            insights.append("You tend to choose restaurants you really enjoy")
        
        if len(user_profile.preferences.favorite_cuisines) > 5:
            insights.append("You're an adventurous eater who enjoys diverse cuisines")
        
        if user_profile.preferences.preferred_price_range in [PriceRange.EXPENSIVE, PriceRange.VERY_EXPENSIVE]:
            insights.append("You prefer upscale dining experiences")
        
        return insights
    
    def _get_most_common_cuisine(self, restaurants: List[Restaurant]) -> Optional[CuisineType]:
        """Get most common cuisine type."""
        cuisine_counter = Counter()
        for restaurant in restaurants:
            for cuisine in restaurant.cuisine_types:
                cuisine_counter[cuisine] += 1
        
        if cuisine_counter:
            return cuisine_counter.most_common(1)[0][0]
        return None
    
    def _get_most_common_price_range(self, restaurants: List[Restaurant]) -> Optional[PriceRange]:
        """Get most common price range."""
        price_counter = Counter()
        for restaurant in restaurants:
            if restaurant.price_range:
                price_counter[restaurant.price_range] += 1
        
        if price_counter:
            return price_counter.most_common(1)[0][0]
        return None
    
    def _get_frequent_locations(self, restaurants: List[Restaurant]) -> List[Location]:
        """Get frequent dining locations."""
        location_counter = Counter()
        location_map = {}
        
        for restaurant in restaurants:
            key = (restaurant.location.city, restaurant.location.state)
            location_counter[key] += 1
            location_map[key] = restaurant.location
        
        frequent_locations = []
        for (city, state), count in location_counter.most_common(3):
            frequent_locations.append(location_map[(city, state)])
        
        return frequent_locations
    
    def _update_preferences_from_feedback(
        self,
        preferences: UserPreferences,
        feedback: SessionFeedback
    ) -> UserPreferences:
        """Update preferences based on user feedback."""
        # Update cuisine preferences
        for cuisine, rating in feedback.cuisine_feedback.items():
            if rating >= 4.0 and cuisine not in preferences.favorite_cuisines:
                preferences.favorite_cuisines.append(cuisine)
            elif rating < 2.0 and cuisine in preferences.favorite_cuisines:
                preferences.favorite_cuisines.remove(cuisine)
        
        # Update vibe preferences
        for vibe, rating in feedback.vibe_feedback.items():
            if rating >= 4.0 and vibe not in preferences.preferred_vibes:
                preferences.preferred_vibes.append(vibe)
            elif rating < 2.0 and vibe in preferences.preferred_vibes:
                preferences.preferred_vibes.remove(vibe)
        
        # Update price preferences
        for price_range, rating in feedback.price_feedback.items():
            if rating >= 4.0:
                preferences.preferred_price_range = price_range
        
        return preferences
    
    def _apply_learned_preferences(
        self,
        context: RecommendationContext,
        learned_preferences: UserPreferences
    ) -> RecommendationContext:
        """Apply learned preferences to recommendation context."""
        # Merge with existing preferences
        if learned_preferences.favorite_cuisines:
            context.cuisine_preferences.extend(learned_preferences.favorite_cuisines)
        
        if learned_preferences.preferred_vibes:
            context.vibe_preferences.extend(learned_preferences.preferred_vibes)
        
        if learned_preferences.preferred_price_range:
            context.price_range = learned_preferences.preferred_price_range
        
        return context