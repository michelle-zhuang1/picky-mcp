"""Automated data enrichment and real-time sync manager."""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import schedule
import time
from threading import Thread

from .notion_client import NotionManager
from .maps_client import GoogleMapsClient
from .restaurant_manager import RestaurantManager
from .config import settings

logger = logging.getLogger(__name__)


class SyncManager:
    """Manages automated data enrichment and real-time synchronization."""
    
    def __init__(self, notion_client: NotionManager, maps_client: GoogleMapsClient, restaurant_manager: RestaurantManager):
        """Initialize sync manager."""
        self.notion = notion_client
        self.maps = maps_client
        self.restaurant_manager = restaurant_manager
        self.is_running = False
        self.sync_thread = None
        self.last_sync = None
    
    def start_sync_scheduler(self):
        """Start the automated sync scheduler."""
        if self.is_running:
            logger.warning("Sync scheduler already running")
            return
        
        self.is_running = True
        
        # Schedule periodic tasks
        schedule.every(1).hours.do(self._sync_recent_changes)
        schedule.every(6).hours.do(self._enrich_missing_data)
        schedule.every(24).hours.do(self._full_database_sync)
        
        # Start scheduler thread
        self.sync_thread = Thread(target=self._run_scheduler, daemon=True)
        self.sync_thread.start()
        
        logger.info("Sync scheduler started")
    
    def stop_sync_scheduler(self):
        """Stop the automated sync scheduler."""
        if not self.is_running:
            logger.warning("Sync scheduler not running")
            return
        
        self.is_running = False
        schedule.clear()
        
        if self.sync_thread:
            self.sync_thread.join(timeout=5)
        
        logger.info("Sync scheduler stopped")
    
    def _run_scheduler(self):
        """Run the scheduler in a separate thread."""
        while self.is_running:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                time.sleep(60)
    
    def _sync_recent_changes(self):
        """Sync recent changes from Notion database."""
        try:
            logger.info("Starting sync of recent changes...")
            
            # Get recent restaurants (last 24 hours)
            recent_restaurants = asyncio.run(self.notion.get_recent_visits(limit=50))
            
            enriched_count = 0
            for restaurant in recent_restaurants:
                try:
                    # Skip if already enriched recently
                    if (restaurant.google_places_data and 
                        restaurant.updated_at and 
                        restaurant.updated_at > datetime.now() - timedelta(hours=24)):
                        continue
                    
                    # Enrich with Google Maps data
                    enriched_restaurant = asyncio.run(self.maps.enrich_restaurant_data(restaurant))
                    
                    if enriched_restaurant.google_places_data:
                        asyncio.run(self.notion.update_restaurant(
                            restaurant.notion_page_id,
                            enriched_restaurant
                        ))
                        enriched_count += 1
                    
                    # Small delay to avoid rate limiting
                    time.sleep(0.2)
                    
                except Exception as e:
                    logger.warning(f"Failed to sync restaurant {restaurant.name}: {e}")
                    continue
            
            self.last_sync = datetime.now()
            logger.info(f"Recent changes sync completed. Enriched {enriched_count} restaurants.")
            
        except Exception as e:
            logger.error(f"Failed to sync recent changes: {e}")
    
    def _enrich_missing_data(self):
        """Enrich restaurants that are missing Google Maps data."""
        try:
            logger.info("Starting enrichment of missing data...")
            
            # Get all restaurants
            all_restaurants = asyncio.run(self.notion.get_all_restaurants())
            
            # Filter restaurants missing Google data
            missing_data_restaurants = [
                r for r in all_restaurants 
                if not r.google_places_data or not r.google_places_data.place_id
            ]
            
            logger.info(f"Found {len(missing_data_restaurants)} restaurants missing Google data")
            
            enriched_count = 0
            for restaurant in missing_data_restaurants[:20]:  # Limit to 20 per run
                try:
                    enriched_restaurant = asyncio.run(self.maps.enrich_restaurant_data(restaurant))
                    
                    if enriched_restaurant.google_places_data:
                        asyncio.run(self.notion.update_restaurant(
                            restaurant.notion_page_id,
                            enriched_restaurant
                        ))
                        enriched_count += 1
                    
                    # Delay to avoid rate limiting
                    time.sleep(0.5)
                    
                except Exception as e:
                    logger.warning(f"Failed to enrich restaurant {restaurant.name}: {e}")
                    continue
            
            logger.info(f"Missing data enrichment completed. Enriched {enriched_count} restaurants.")
            
        except Exception as e:
            logger.error(f"Failed to enrich missing data: {e}")
    
    def _full_database_sync(self):
        """Perform full database synchronization."""
        try:
            logger.info("Starting full database sync...")
            
            # Get all restaurants
            all_restaurants = asyncio.run(self.notion.get_all_restaurants())
            
            # Update all restaurant data
            updated_count = 0
            for restaurant in all_restaurants:
                try:
                    # Check if data is stale (older than 7 days)
                    if (restaurant.updated_at and 
                        restaurant.updated_at > datetime.now() - timedelta(days=7)):
                        continue
                    
                    # Re-enrich with latest Google Maps data
                    enriched_restaurant = asyncio.run(self.maps.enrich_restaurant_data(restaurant))
                    
                    if enriched_restaurant.google_places_data:
                        asyncio.run(self.notion.update_restaurant(
                            restaurant.notion_page_id,
                            enriched_restaurant
                        ))
                        updated_count += 1
                    
                    # Delay to avoid rate limiting
                    time.sleep(1)
                    
                except Exception as e:
                    logger.warning(f"Failed to sync restaurant {restaurant.name}: {e}")
                    continue
            
            logger.info(f"Full database sync completed. Updated {updated_count} restaurants.")
            
        except Exception as e:
            logger.error(f"Failed to perform full database sync: {e}")
    
    async def manual_sync(self) -> Dict[str, Any]:
        """Perform manual synchronization."""
        try:
            logger.info("Starting manual synchronization...")
            
            # Get all restaurants
            all_restaurants = await self.notion.get_all_restaurants()
            
            sync_results = {
                "total_restaurants": len(all_restaurants),
                "enriched_count": 0,
                "updated_count": 0,
                "failed_count": 0,
                "errors": []
            }
            
            for restaurant in all_restaurants:
                try:
                    # Enrich with Google Maps data
                    enriched_restaurant = await self.maps.enrich_restaurant_data(restaurant)
                    
                    if enriched_restaurant.google_places_data:
                        # Update in Notion
                        result = await self.notion.update_restaurant(
                            restaurant.notion_page_id,
                            enriched_restaurant
                        )
                        
                        if result["success"]:
                            if restaurant.google_places_data:
                                sync_results["updated_count"] += 1
                            else:
                                sync_results["enriched_count"] += 1
                        else:
                            sync_results["failed_count"] += 1
                            sync_results["errors"].append(f"Failed to update {restaurant.name}: {result.get('error', 'Unknown error')}")
                    
                    # Small delay to avoid rate limiting
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    sync_results["failed_count"] += 1
                    sync_results["errors"].append(f"Failed to process {restaurant.name}: {str(e)}")
                    logger.warning(f"Failed to sync restaurant {restaurant.name}: {e}")
                    continue
            
            self.last_sync = datetime.now()
            
            logger.info(f"Manual sync completed. Enriched: {sync_results['enriched_count']}, Updated: {sync_results['updated_count']}, Failed: {sync_results['failed_count']}")
            
            return {
                "success": True,
                "results": sync_results,
                "last_sync": self.last_sync.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Manual sync failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def sync_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Sync user profile based on latest Notion data."""
        try:
            logger.info(f"Syncing user profile for {user_id}...")
            
            # Force update of user profile
            await self.restaurant_manager._update_user_profile(user_id)
            
            # Get updated profile
            profile = await self.restaurant_manager._get_or_create_user_profile(user_id)
            
            return {
                "success": True,
                "message": f"User profile synced successfully for {user_id}",
                "profile": {
                    "total_restaurants": profile.total_restaurants,
                    "average_rating": profile.average_rating,
                    "dining_personality": profile.dining_personality,
                    "favorite_cuisines": [c.value for c in profile.preferences.favorite_cuisines],
                    "last_updated": profile.updated_at.isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to sync user profile: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def detect_notion_changes(self) -> List[Dict[str, Any]]:
        """Detect changes in Notion database since last sync."""
        try:
            if not self.last_sync:
                # If no previous sync, consider all restaurants as new
                restaurants = await self.notion.get_all_restaurants()
                return [{"type": "new", "restaurant": r.name} for r in restaurants]
            
            # Get recent visits since last sync
            recent_restaurants = await self.notion.get_recent_visits(limit=100)
            
            changes = []
            for restaurant in recent_restaurants:
                if restaurant.updated_at and restaurant.updated_at > self.last_sync:
                    if restaurant.date_visited and restaurant.date_visited > self.last_sync:
                        changes.append({
                            "type": "new_visit",
                            "restaurant": restaurant.name,
                            "date": restaurant.date_visited.isoformat()
                        })
                    else:
                        changes.append({
                            "type": "updated",
                            "restaurant": restaurant.name,
                            "updated": restaurant.updated_at.isoformat()
                        })
            
            return changes
            
        except Exception as e:
            logger.error(f"Failed to detect Notion changes: {e}")
            return []
    
    def get_sync_status(self) -> Dict[str, Any]:
        """Get current sync status."""
        return {
            "is_running": self.is_running,
            "last_sync": self.last_sync.isoformat() if self.last_sync else None,
            "next_sync": schedule.next_run().isoformat() if schedule.jobs else None,
            "scheduled_jobs": len(schedule.jobs)
        }