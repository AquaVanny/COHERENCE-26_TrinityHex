"""
Geocoding Service using Nominatim (OpenStreetMap) API
Converts addresses to lat/lon coordinates with caching to minimize API calls.
"""
import requests
import time
import json
import os
from typing import Optional, Tuple, Dict
from functools import lru_cache

# Nominatim API endpoint (free, no API key required)
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

# User agent required by Nominatim usage policy
USER_AGENT = "ClinicalTrialMatcher/1.0 (Healthcare Research)"

# Cache file for geocoded locations
CACHE_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'geocode_cache.json')

# In-memory cache
_geocode_cache: Dict[str, Tuple[float, float]] = {}
_cache_loaded = False


def _load_cache():
    """Load geocode cache from disk."""
    global _geocode_cache, _cache_loaded
    if _cache_loaded:
        return
    
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, 'r') as f:
                _geocode_cache = {k: tuple(v) for k, v in json.load(f).items()}
    except Exception as e:
        print(f"Warning: Could not load geocode cache: {e}")
    
    _cache_loaded = True


def _save_cache():
    """Save geocode cache to disk."""
    try:
        os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
        with open(CACHE_FILE, 'w') as f:
            json.dump({k: list(v) for k, v in _geocode_cache.items()}, f, indent=2)
    except Exception as e:
        print(f"Warning: Could not save geocode cache: {e}")


def geocode_location(location_str: str) -> Optional[Tuple[float, float]]:
    """
    Convert a location string (city, state, address) to (lat, lon) coordinates.
    Uses Nominatim API with caching to minimize requests.
    
    Args:
        location_str: Address string (e.g., "Boston, MA" or "San Francisco, CA")
    
    Returns:
        Tuple of (latitude, longitude) or None if geocoding fails
    """
    if not location_str:
        return None
    
    # Normalize the location string
    location_key = location_str.strip().lower()
    
    # Load cache if not already loaded
    _load_cache()
    
    # Check cache first
    if location_key in _geocode_cache:
        return _geocode_cache[location_key]
    
    # Call Nominatim API
    try:
        params = {
            'q': location_str,
            'format': 'json',
            'limit': 1,
            'countrycodes': 'us',  # Restrict to US for clinical trials
        }
        
        headers = {
            'User-Agent': USER_AGENT
        }
        
        response = requests.get(NOMINATIM_URL, params=params, headers=headers, timeout=5)
        response.raise_for_status()
        
        data = response.json()
        
        if data and len(data) > 0:
            lat = float(data[0]['lat'])
            lon = float(data[0]['lon'])
            coords = (lat, lon)
            
            # Cache the result
            _geocode_cache[location_key] = coords
            _save_cache()
            
            # Respect Nominatim usage policy: max 1 request per second
            time.sleep(1)
            
            return coords
        
    except Exception as e:
        print(f"Geocoding failed for '{location_str}': {e}")
    
    return None


def geocode_multiple(locations: list) -> Dict[str, Optional[Tuple[float, float]]]:
    """
    Geocode multiple locations in batch.
    
    Args:
        locations: List of location strings
    
    Returns:
        Dict mapping location string to (lat, lon) or None
    """
    results = {}
    for loc in locations:
        results[loc] = geocode_location(loc)
    return results


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate distance in miles between two lat/lon points using Haversine formula.
    
    Args:
        lat1, lon1: First point coordinates
        lat2, lon2: Second point coordinates
    
    Returns:
        Distance in miles
    """
    import math
    
    R = 3959  # Earth radius in miles
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c


def get_cache_stats() -> Dict:
    """Get statistics about the geocode cache."""
    _load_cache()
    return {
        'cached_locations': len(_geocode_cache),
        'cache_file': CACHE_FILE,
        'cache_exists': os.path.exists(CACHE_FILE)
    }


def clear_cache():
    """Clear the geocode cache (for testing/maintenance)."""
    global _geocode_cache
    _geocode_cache = {}
    if os.path.exists(CACHE_FILE):
        os.remove(CACHE_FILE)
