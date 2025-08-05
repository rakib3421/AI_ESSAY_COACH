"""
Caching module for the Essay Revision Application
Provides in-memory caching for AI analysis results to avoid redundant API calls
"""
import hashlib
import json
import time
import logging
from typing import Dict, Any, Optional
from collections import OrderedDict
from config import Config

logger = logging.getLogger(__name__)

class LRUCache:
    """
    Least Recently Used (LRU) cache implementation for AI analysis results
    """
    
    def __init__(self, max_size: int = 1000, ttl: int = 3600):
        """
        Initialize LRU cache
        
        Args:
            max_size (int): Maximum number of items to cache
            ttl (int): Time to live for cache entries in seconds
        """
        self.max_size = max_size
        self.ttl = ttl
        self.cache: OrderedDict = OrderedDict()
        self.timestamps: Dict[str, float] = {}
        
    def _generate_cache_key(self, essay_text: str, essay_type: str = 'auto', 
                           coaching_level: str = 'medium', 
                           suggestion_aggressiveness: str = 'medium') -> str:
        """
        Generate a unique cache key for the given parameters
        
        Args:
            essay_text (str): The essay content
            essay_type (str): Type of essay analysis
            coaching_level (str): Level of coaching
            suggestion_aggressiveness (str): Aggressiveness of suggestions
            
        Returns:
            str: SHA-256 hash as cache key
        """
        # Create a string representation of all parameters
        cache_input = f"{essay_text.strip()}{essay_type}{coaching_level}{suggestion_aggressiveness}"
        
        # Generate SHA-256 hash
        return hashlib.sha256(cache_input.encode('utf-8')).hexdigest()
    
    def _is_expired(self, key: str) -> bool:
        """
        Check if a cache entry has expired
        
        Args:
            key (str): Cache key
            
        Returns:
            bool: True if expired, False otherwise
        """
        if key not in self.timestamps:
            return True
        
        return (time.time() - self.timestamps[key]) > self.ttl
    
    def _cleanup_expired(self):
        """Remove expired entries from cache"""
        current_time = time.time()
        expired_keys = [
            key for key, timestamp in self.timestamps.items()
            if (current_time - timestamp) > self.ttl
        ]
        
        for key in expired_keys:
            self._remove_entry(key)
        
        if expired_keys:
            logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")
    
    def _remove_entry(self, key: str):
        """Remove a specific entry from cache"""
        if key in self.cache:
            del self.cache[key]
        if key in self.timestamps:
            del self.timestamps[key]
    
    def _evict_oldest(self):
        """Remove the oldest entry from cache"""
        if self.cache:
            oldest_key = next(iter(self.cache))
            self._remove_entry(oldest_key)
            logger.debug(f"Evicted oldest cache entry: {oldest_key[:16]}...")
    
    def get(self, essay_text: str, essay_type: str = 'auto', 
            coaching_level: str = 'medium', 
            suggestion_aggressiveness: str = 'medium') -> Optional[Dict[str, Any]]:
        """
        Retrieve analysis from cache
        
        Args:
            essay_text (str): The essay content
            essay_type (str): Type of essay analysis
            coaching_level (str): Level of coaching
            suggestion_aggressiveness (str): Aggressiveness of suggestions
            
        Returns:
            Dict[str, Any] or None: Cached analysis or None if not found/expired
        """
        if not Config.PERFORMANCE.get('cache_enabled', True):
            return None
        
        # Clean up expired entries periodically
        self._cleanup_expired()
        
        key = self._generate_cache_key(essay_text, essay_type, coaching_level, suggestion_aggressiveness)
        
        # Check if entry exists and is not expired
        if key in self.cache and not self._is_expired(key):
            # Move to end (mark as recently used)
            self.cache.move_to_end(key)
            logger.info(f"Cache hit for analysis: {key[:16]}...")
            return self.cache[key]
        
        # Remove expired entry if it exists
        if key in self.cache:
            self._remove_entry(key)
        
        logger.debug(f"Cache miss for analysis: {key[:16]}...")
        return None
    
    def set(self, essay_text: str, analysis_result: Dict[str, Any], 
            essay_type: str = 'auto', coaching_level: str = 'medium', 
            suggestion_aggressiveness: str = 'medium'):
        """
        Store analysis in cache
        
        Args:
            essay_text (str): The essay content
            analysis_result (Dict[str, Any]): Analysis result to cache
            essay_type (str): Type of essay analysis
            coaching_level (str): Level of coaching
            suggestion_aggressiveness (str): Aggressiveness of suggestions
        """
        if not Config.PERFORMANCE.get('cache_enabled', True):
            return
        
        key = self._generate_cache_key(essay_text, essay_type, coaching_level, suggestion_aggressiveness)
        
        # Remove expired entries before adding new one
        self._cleanup_expired()
        
        # Check if we need to evict entries to make space
        while len(self.cache) >= self.max_size:
            self._evict_oldest()
        
        # Store the analysis result
        self.cache[key] = analysis_result.copy()  # Store a copy to avoid mutations
        self.timestamps[key] = time.time()
        
        logger.info(f"Cached analysis result: {key[:16]}... (cache size: {len(self.cache)})")
    
    def clear(self):
        """Clear all cache entries"""
        self.cache.clear()
        self.timestamps.clear()
        logger.info("Cache cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics
        
        Returns:
            Dict[str, Any]: Cache statistics
        """
        current_time = time.time()
        expired_count = sum(
            1 for timestamp in self.timestamps.values()
            if (current_time - timestamp) > self.ttl
        )
        
        return {
            'total_entries': len(self.cache),
            'expired_entries': expired_count,
            'active_entries': len(self.cache) - expired_count,
            'max_size': self.max_size,
            'ttl_seconds': self.ttl,
            'cache_enabled': Config.PERFORMANCE.get('cache_enabled', True)
        }

# Global cache instance
analysis_cache = LRUCache(
    max_size=Config.PERFORMANCE.get('cache_max_size', 1000),
    ttl=Config.PERFORMANCE.get('cache_ttl', 3600)
)

def get_cached_analysis(essay_text: str, essay_type: str = 'auto', 
                       coaching_level: str = 'medium', 
                       suggestion_aggressiveness: str = 'medium') -> Optional[Dict[str, Any]]:
    """
    Get cached analysis result
    
    Args:
        essay_text (str): The essay content
        essay_type (str): Type of essay analysis
        coaching_level (str): Level of coaching
        suggestion_aggressiveness (str): Aggressiveness of suggestions
        
    Returns:
        Dict[str, Any] or None: Cached analysis or None if not found
    """
    return analysis_cache.get(essay_text, essay_type, coaching_level, suggestion_aggressiveness)

def cache_analysis(essay_text: str, analysis_result: Dict[str, Any], 
                  essay_type: str = 'auto', coaching_level: str = 'medium', 
                  suggestion_aggressiveness: str = 'medium'):
    """
    Cache analysis result
    
    Args:
        essay_text (str): The essay content
        analysis_result (Dict[str, Any]): Analysis result to cache
        essay_type (str): Type of essay analysis
        coaching_level (str): Level of coaching
        suggestion_aggressiveness (str): Aggressiveness of suggestions
    """
    analysis_cache.set(essay_text, analysis_result, essay_type, coaching_level, suggestion_aggressiveness)

def clear_cache():
    """Clear all cached analyses"""
    analysis_cache.clear()

def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics"""
    return analysis_cache.get_stats()
