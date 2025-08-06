"""
Monitoring and Caching module for the Essay Revision Application
Combines performance monitoring and caching functionality
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
        self.timestamps: Dict = {}
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'size': 0
        }
    
    def _is_expired(self, key: str) -> bool:
        """Check if cache entry is expired"""
        if key not in self.timestamps:
            return True
        return time.time() - self.timestamps[key] > self.ttl
    
    def _evict_expired(self):
        """Remove expired entries from cache"""
        current_time = time.time()
        expired_keys = [
            key for key, timestamp in self.timestamps.items()
            if current_time - timestamp > self.ttl
        ]
        
        for key in expired_keys:
            if key in self.cache:
                del self.cache[key]
                del self.timestamps[key]
                self.stats['evictions'] += 1
        
        self.stats['size'] = len(self.cache)
    
    def get(self, key: str) -> Optional[Any]:
        """Get item from cache"""
        self._evict_expired()
        
        if key in self.cache and not self._is_expired(key):
            # Move to end (most recently used)
            self.cache.move_to_end(key)
            self.stats['hits'] += 1
            return self.cache[key]
        
        self.stats['misses'] += 1
        return None
    
    def put(self, key: str, value: Any):
        """Put item in cache"""
        self._evict_expired()
        
        if key in self.cache:
            # Update existing entry
            self.cache[key] = value
            self.cache.move_to_end(key)
        else:
            # Add new entry
            if len(self.cache) >= self.max_size:
                # Remove least recently used
                oldest_key = next(iter(self.cache))
                del self.cache[oldest_key]
                del self.timestamps[oldest_key]
                self.stats['evictions'] += 1
            
            self.cache[key] = value
        
        self.timestamps[key] = time.time()
        self.stats['size'] = len(self.cache)
    
    def clear(self):
        """Clear all cache entries"""
        self.cache.clear()
        self.timestamps.clear()
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'size': 0
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        self._evict_expired()
        total_requests = self.stats['hits'] + self.stats['misses']
        hit_rate = (self.stats['hits'] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            **self.stats,
            'hit_rate': round(hit_rate, 2),
            'total_requests': total_requests,
            'max_size': self.max_size,
            'ttl': self.ttl
        }

class PerformanceMonitor:
    """
    Performance monitoring utility to track system performance metrics
    """
    
    def __init__(self):
        """Initialize performance monitor"""
        self.reset_stats()
    
    def reset_stats(self):
        """Reset all performance statistics"""
        self.stats = {
            # AI Analysis stats
            'ai_analysis': {
                'total_requests': 0,
                'cache_hits': 0,
                'cache_misses': 0,
                'total_analysis_time': 0.0,
                'avg_analysis_time': 0.0,
                'failed_requests': 0,
                'successful_requests': 0
            },
            
            # Database stats
            'database': {
                'total_queries': 0,
                'total_connection_time': 0.0,
                'avg_connection_time': 0.0,
                'failed_connections': 0,
                'successful_connections': 0,
                'pool_hits': 0,
                'pool_misses': 0
            },
            
            # File handling stats
            'file_handling': {
                'total_uploads': 0,
                'total_upload_size': 0,
                'avg_upload_size': 0.0,
                'streamed_files': 0,
                'failed_uploads': 0,
                'successful_uploads': 0
            },
            
            # System stats
            'system': {
                'start_time': time.time(),
                'uptime': 0.0,
                'memory_usage': 0.0,
                'active_connections': 0
            }
        }
    
    def record_ai_analysis(self, execution_time: float, cached: bool = False, success: bool = True):
        """Record AI analysis performance metrics"""
        self.stats['ai_analysis']['total_requests'] += 1
        
        if cached:
            self.stats['ai_analysis']['cache_hits'] += 1
        else:
            self.stats['ai_analysis']['cache_misses'] += 1
            self.stats['ai_analysis']['total_analysis_time'] += execution_time
        
        if success:
            self.stats['ai_analysis']['successful_requests'] += 1
        else:
            self.stats['ai_analysis']['failed_requests'] += 1
        
        # Update average
        non_cached_requests = self.stats['ai_analysis']['cache_misses']
        if non_cached_requests > 0:
            self.stats['ai_analysis']['avg_analysis_time'] = (
                self.stats['ai_analysis']['total_analysis_time'] / non_cached_requests
            )
    
    def record_database_operation(self, connection_time: float, success: bool = True, pooled: bool = False):
        """Record database operation performance metrics"""
        self.stats['database']['total_queries'] += 1
        self.stats['database']['total_connection_time'] += connection_time
        
        if success:
            self.stats['database']['successful_connections'] += 1
        else:
            self.stats['database']['failed_connections'] += 1
        
        if pooled:
            self.stats['database']['pool_hits'] += 1
        else:
            self.stats['database']['pool_misses'] += 1
        
        # Update average
        total_queries = self.stats['database']['total_queries']
        if total_queries > 0:
            self.stats['database']['avg_connection_time'] = (
                self.stats['database']['total_connection_time'] / total_queries
            )
    
    def record_file_upload(self, file_size: int, streamed: bool = False, success: bool = True):
        """Record file upload performance metrics"""
        self.stats['file_handling']['total_uploads'] += 1
        
        if success:
            self.stats['file_handling']['successful_uploads'] += 1
            self.stats['file_handling']['total_upload_size'] += file_size
            
            if streamed:
                self.stats['file_handling']['streamed_files'] += 1
        else:
            self.stats['file_handling']['failed_uploads'] += 1
        
        # Update average
        successful_uploads = self.stats['file_handling']['successful_uploads']
        if successful_uploads > 0:
            self.stats['file_handling']['avg_upload_size'] = (
                self.stats['file_handling']['total_upload_size'] / successful_uploads
            )
    
    def update_system_stats(self, memory_usage: float = None, active_connections: int = None):
        """Update system performance metrics"""
        self.stats['system']['uptime'] = time.time() - self.stats['system']['start_time']
        
        if memory_usage is not None:
            self.stats['system']['memory_usage'] = memory_usage
        
        if active_connections is not None:
            self.stats['system']['active_connections'] = active_connections
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary"""
        self.update_system_stats()
        
        summary = {
            'ai_analysis': {
                'total_requests': self.stats['ai_analysis']['total_requests'],
                'success_rate': self._calculate_success_rate(
                    self.stats['ai_analysis']['successful_requests'],
                    self.stats['ai_analysis']['total_requests']
                ),
                'cache_hit_rate': self._calculate_hit_rate(
                    self.stats['ai_analysis']['cache_hits'],
                    self.stats['ai_analysis']['total_requests']
                ),
                'avg_analysis_time': round(self.stats['ai_analysis']['avg_analysis_time'], 3)
            },
            
            'database': {
                'total_queries': self.stats['database']['total_queries'],
                'success_rate': self._calculate_success_rate(
                    self.stats['database']['successful_connections'],
                    self.stats['database']['total_queries']
                ),
                'pool_hit_rate': self._calculate_hit_rate(
                    self.stats['database']['pool_hits'],
                    self.stats['database']['total_queries']
                ),
                'avg_connection_time': round(self.stats['database']['avg_connection_time'], 3)
            },
            
            'file_handling': {
                'total_uploads': self.stats['file_handling']['total_uploads'],
                'success_rate': self._calculate_success_rate(
                    self.stats['file_handling']['successful_uploads'],
                    self.stats['file_handling']['total_uploads']
                ),
                'streaming_rate': self._calculate_hit_rate(
                    self.stats['file_handling']['streamed_files'],
                    self.stats['file_handling']['successful_uploads']
                ),
                'avg_upload_size_mb': round(self.stats['file_handling']['avg_upload_size'] / (1024*1024), 2)
            },
            
            'system': {
                'uptime_hours': round(self.stats['system']['uptime'] / 3600, 2),
                'memory_usage_mb': round(self.stats['system']['memory_usage'], 2),
                'active_connections': self.stats['system']['active_connections']
            }
        }
        
        return summary
    
    def _calculate_success_rate(self, successful: int, total: int) -> float:
        """Calculate success rate percentage"""
        return round((successful / total * 100) if total > 0 else 0, 2)
    
    def _calculate_hit_rate(self, hits: int, total: int) -> float:
        """Calculate hit rate percentage"""
        return round((hits / total * 100) if total > 0 else 0, 2)
    
    def get_detailed_stats(self) -> Dict[str, Any]:
        """Get detailed statistics for all components"""
        self.update_system_stats()
        return self.stats.copy()

# Global instances
_cache = LRUCache(
    max_size=Config.PERFORMANCE.get('cache_max_size', 1000),
    ttl=Config.PERFORMANCE.get('cache_ttl', 3600)
)
_monitor = PerformanceMonitor()

def generate_cache_key(text: str, essay_type: str = "", analysis_type: str = "full") -> str:
    """
    Generate a unique cache key for essay analysis
    
    Args:
        text (str): Essay text content
        essay_type (str): Type of essay
        analysis_type (str): Type of analysis requested
    
    Returns:
        str: Unique cache key
    """
    content = f"{text}_{essay_type}_{analysis_type}"
    return hashlib.md5(content.encode('utf-8')).hexdigest()

def get_cached_analysis(cache_key: str) -> Optional[Dict[str, Any]]:
    """Get cached analysis result"""
    return _cache.get(cache_key)

def cache_analysis(cache_key: str, analysis_result: Dict[str, Any]):
    """Cache analysis result"""
    _cache.put(cache_key, analysis_result)

def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics"""
    return _cache.get_stats()

def clear_cache():
    """Clear all cached analyses"""
    _cache.clear()

def record_ai_analysis(execution_time: float, cached: bool = False, success: bool = True):
    """Record AI analysis performance"""
    _monitor.record_ai_analysis(execution_time, cached, success)

def record_database_operation(connection_time: float, success: bool = True, pooled: bool = False):
    """Record database operation performance"""
    _monitor.record_database_operation(connection_time, success, pooled)

def record_file_upload(file_size: int, streamed: bool = False, success: bool = True):
    """Record file upload performance"""
    _monitor.record_file_upload(file_size, streamed, success)

def get_performance_summary() -> Dict[str, Any]:
    """Get performance summary"""
    return _monitor.get_performance_summary()

def get_detailed_performance_stats() -> Dict[str, Any]:
    """Get detailed performance statistics"""
    return _monitor.get_detailed_stats()

def reset_performance_stats():
    """Reset all performance statistics"""
    _monitor.reset_stats()
