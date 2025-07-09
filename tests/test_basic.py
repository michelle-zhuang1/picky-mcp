#!/usr/bin/env python3
"""Basic tests for the Restaurant Recommendation MCP Server."""

import sys
import os
import pytest
import asyncio
from unittest.mock import Mock, patch

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.models import Restaurant, Location, CuisineType, PriceRange, VibeType
from src.config import validate_configuration

def test_configuration_validation():
    """Test configuration validation."""
    # This test will fail without proper environment variables
    # but it demonstrates the validation functionality
    config_status = validate_configuration()
    
    assert isinstance(config_status, dict)
    assert "valid" in config_status
    assert "message" in config_status
    assert "settings" in config_status

def test_restaurant_model():
    """Test Restaurant model creation."""
    location = Location(
        city="New York",
        state="NY",
        latitude=40.7589,
        longitude=-73.9851
    )
    
    restaurant = Restaurant(
        name="Test Restaurant",
        location=location,
        cuisine_types=[CuisineType.ITALIAN],
        price_range=PriceRange.MODERATE,
        vibes=[VibeType.CASUAL],
        personal_rating=4.5,
        notes="Great pizza!"
    )
    
    assert restaurant.name == "Test Restaurant"
    assert restaurant.location.city == "New York"
    assert restaurant.personal_rating == 4.5
    assert CuisineType.ITALIAN in restaurant.cuisine_types
    assert restaurant.price_range == PriceRange.MODERATE

def test_location_model():
    """Test Location model creation."""
    location = Location(
        address="123 Main St",
        city="Seattle",
        state="WA",
        latitude=47.6062,
        longitude=-122.3321
    )
    
    assert location.address == "123 Main St"
    assert location.city == "Seattle"
    assert location.state == "WA"
    assert location.latitude == 47.6062
    assert location.longitude == -122.3321

def test_cuisine_type_enum():
    """Test CuisineType enum."""
    assert CuisineType.ITALIAN.value == "Italian"
    assert CuisineType.JAPANESE.value == "Japanese"
    assert CuisineType.MEXICAN.value == "Mexican"

def test_price_range_enum():
    """Test PriceRange enum."""
    assert PriceRange.BUDGET.value == "$"
    assert PriceRange.MODERATE.value == "$$"
    assert PriceRange.EXPENSIVE.value == "$$$"
    assert PriceRange.VERY_EXPENSIVE.value == "$$$$"

def test_vibe_type_enum():
    """Test VibeType enum."""
    assert VibeType.CASUAL.value == "casual"
    assert VibeType.ROMANTIC.value == "romantic"
    assert VibeType.FAMILY_FRIENDLY.value == "family-friendly"

if __name__ == "__main__":
    print("🧪 Running basic tests...")
    
    try:
        test_configuration_validation()
        print("✅ Configuration validation test passed")
    except Exception as e:
        print(f"⚠️  Configuration validation test failed: {e}")
    
    try:
        test_restaurant_model()
        print("✅ Restaurant model test passed")
    except Exception as e:
        print(f"❌ Restaurant model test failed: {e}")
    
    try:
        test_location_model()
        print("✅ Location model test passed")
    except Exception as e:
        print(f"❌ Location model test failed: {e}")
    
    try:
        test_cuisine_type_enum()
        print("✅ CuisineType enum test passed")
    except Exception as e:
        print(f"❌ CuisineType enum test failed: {e}")
    
    try:
        test_price_range_enum()
        print("✅ PriceRange enum test passed")
    except Exception as e:
        print(f"❌ PriceRange enum test failed: {e}")
    
    try:
        test_vibe_type_enum()
        print("✅ VibeType enum test passed")
    except Exception as e:
        print(f"❌ VibeType enum test failed: {e}")
    
    print("\\n🎉 Basic tests completed!")