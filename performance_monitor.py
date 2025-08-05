"""
Performance monitoring module for the Essay Revision Application
Provides monitoring and statistics for caching, database pooling, and file streaming
"""
import time
import logging
from typing import Dict, Any, Optional
from config import Config

logger = logging.getLogger(__name__)

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
                'fastest_analysis': float('inf'),
                'slowest_analysis': 0.0
            },
            
            # Database stats
            'database': {
                'total_queries': 0,
                'total_query_time': 0.0,
                'avg_query_time': 0.0,
                'connection_pool_enabled': Config.PERFORMANCE.get('db_pool_enabled', False),
                'pooled_connections': 0,
                'direct_connections': 0
            },
            
            # File handling stats
            'file_handling': {
                'total_uploads': 0,
                'streamed_uploads': 0,
                'memory_uploads': 0,
                'total_upload_size': 0,
                'avg_upload_size': 0.0,
                'largest_upload': 0,
                'streaming_enabled': Config.PERFORMANCE.get('file_streaming_enabled', False)
            },
            
            # System stats
            'system': {
                'startup_time': time.time(),
                'uptime': 0.0
            }
        }
    
    def record_ai_analysis(self, analysis_time: float, was_cached: bool = False):
        """
        Record AI analysis performance metrics
        
        Args:
            analysis_time (float): Time taken for analysis in seconds
            was_cached (bool): Whether result was from cache
        """
        ai_stats = self.stats['ai_analysis']
        ai_stats['total_requests'] += 1
        
        if was_cached:
            ai_stats['cache_hits'] += 1
        else:
            ai_stats['cache_misses'] += 1
            ai_stats['total_analysis_time'] += analysis_time
            ai_stats['fastest_analysis'] = min(ai_stats['fastest_analysis'], analysis_time)
            ai_stats['slowest_analysis'] = max(ai_stats['slowest_analysis'], analysis_time)
        
        # Calculate average (excluding cached requests)
        non_cached_requests = ai_stats['cache_misses']
        if non_cached_requests > 0:
            ai_stats['avg_analysis_time'] = ai_stats['total_analysis_time'] / non_cached_requests
    
    def record_database_query(self, query_time: float, is_pooled: bool = False):
        """
        Record database query performance metrics
        
        Args:
            query_time (float): Time taken for query in seconds
            is_pooled (bool): Whether connection was from pool
        """
        db_stats = self.stats['database']
        db_stats['total_queries'] += 1
        db_stats['total_query_time'] += query_time
        db_stats['avg_query_time'] = db_stats['total_query_time'] / db_stats['total_queries']
        
        if is_pooled:
            db_stats['pooled_connections'] += 1
        else:
            db_stats['direct_connections'] += 1
    
    def record_file_upload(self, file_size: int, was_streamed: bool = False):
        """
        Record file upload performance metrics
        
        Args:
            file_size (int): Size of uploaded file in bytes
            was_streamed (bool): Whether file was streamed
        """
        file_stats = self.stats['file_handling']
        file_stats['total_uploads'] += 1
        file_stats['total_upload_size'] += file_size
        file_stats['avg_upload_size'] = file_stats['total_upload_size'] / file_stats['total_uploads']
        file_stats['largest_upload'] = max(file_stats['largest_upload'], file_size)
        
        if was_streamed:
            file_stats['streamed_uploads'] += 1
        else:
            file_stats['memory_uploads'] += 1
    
    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive performance statistics
        
        Returns:
            Dict[str, Any]: Complete performance statistics
        """
        # Update uptime
        self.stats['system']['uptime'] = time.time() - self.stats['system']['startup_time']
        
        # Get cache statistics if available
        cache_stats = {}
        try:
            from cache import get_cache_stats
            cache_stats = get_cache_stats()
        except ImportError:
            cache_stats = {'cache_available': False}
        
        # Get database pool statistics if available
        pool_stats = {}
        try:
            from db_pool import get_pool_stats
            pool_stats = get_pool_stats()
        except ImportError:
            pool_stats = {'pool_available': False}
        
        # Get file streaming statistics
        streaming_stats = {}
        try:
            from file_streaming import get_file_streaming_stats
            streaming_stats = get_file_streaming_stats()
        except ImportError:
            streaming_stats = {'streaming_available': False}
        
        return {
            'performance_stats': self.stats,
            'cache_stats': cache_stats,
            'pool_stats': pool_stats,
            'streaming_stats': streaming_stats,
            'configuration': {
                'cache_enabled': Config.PERFORMANCE.get('cache_enabled', False),
                'db_pool_enabled': Config.PERFORMANCE.get('db_pool_enabled', False),
                'file_streaming_enabled': Config.PERFORMANCE.get('file_streaming_enabled', False)
            }
        }
    
    def get_cache_hit_ratio(self) -> float:
        """
        Get cache hit ratio
        
        Returns:
            float: Cache hit ratio (0.0 to 1.0)
        """
        ai_stats = self.stats['ai_analysis']
        total_requests = ai_stats['total_requests']
        
        if total_requests == 0:
            return 0.0
        
        return ai_stats['cache_hits'] / total_requests
    
    def get_pool_usage_ratio(self) -> float:
        """
        Get database pool usage ratio
        
        Returns:
            float: Pool usage ratio (0.0 to 1.0)
        """
        db_stats = self.stats['database']
        total_connections = db_stats['pooled_connections'] + db_stats['direct_connections']
        
        if total_connections == 0:
            return 0.0
        
        return db_stats['pooled_connections'] / total_connections
    
    def get_streaming_usage_ratio(self) -> float:
        """
        Get file streaming usage ratio
        
        Returns:
            float: Streaming usage ratio (0.0 to 1.0)
        """
        file_stats = self.stats['file_handling']
        total_uploads = file_stats['total_uploads']
        
        if total_uploads == 0:
            return 0.0
        
        return file_stats['streamed_uploads'] / total_uploads
    
    def log_performance_summary(self):
        """Log a summary of performance statistics"""
        stats = self.get_comprehensive_stats()
        
        logger.info("=== Performance Summary ===")
        logger.info(f"Uptime: {stats['performance_stats']['system']['uptime']:.2f} seconds")
        
        # AI Analysis
        ai_stats = stats['performance_stats']['ai_analysis']
        if ai_stats['total_requests'] > 0:
            logger.info(f"AI Analysis - Total: {ai_stats['total_requests']}, Cache Hit Ratio: {self.get_cache_hit_ratio():.2%}")
            if ai_stats['cache_misses'] > 0:
                logger.info(f"AI Analysis - Avg Time: {ai_stats['avg_analysis_time']:.2f}s")
        
        # Database
        db_stats = stats['performance_stats']['database']
        if db_stats['total_queries'] > 0:
            logger.info(f"Database - Total Queries: {db_stats['total_queries']}, Pool Usage: {self.get_pool_usage_ratio():.2%}")
            logger.info(f"Database - Avg Query Time: {db_stats['avg_query_time']:.3f}s")
        
        # File Handling
        file_stats = stats['performance_stats']['file_handling']
        if file_stats['total_uploads'] > 0:
            logger.info(f"Files - Total Uploads: {file_stats['total_uploads']}, Streaming Ratio: {self.get_streaming_usage_ratio():.2%}")
            logger.info(f"Files - Avg Size: {file_stats['avg_upload_size'] / 1024:.1f}KB")

# Global performance monitor instance
performance_monitor = PerformanceMonitor()

def record_ai_analysis_time(analysis_time: float, was_cached: bool = False):
    """Record AI analysis performance"""
    performance_monitor.record_ai_analysis(analysis_time, was_cached)

def record_db_query_time(query_time: float, is_pooled: bool = False):
    """Record database query performance"""
    performance_monitor.record_database_query(query_time, is_pooled)

def record_file_upload_stats(file_size: int, was_streamed: bool = False):
    """Record file upload performance"""
    performance_monitor.record_file_upload(file_size, was_streamed)

def get_performance_stats() -> Dict[str, Any]:
    """Get all performance statistics"""
    return performance_monitor.get_comprehensive_stats()

def log_performance_summary():
    """Log performance summary"""
    performance_monitor.log_performance_summary()

def reset_performance_stats():
    """Reset all performance statistics"""
    performance_monitor.reset_stats()

# Context managers for performance tracking
class AIAnalysisTimer:
    """Context manager for timing AI analysis operations"""
    
    def __init__(self, was_cached: bool = False):
        self.was_cached = was_cached
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = time.time() - self.start_time
            record_ai_analysis_time(duration, self.was_cached)

class DatabaseQueryTimer:
    """Context manager for timing database query operations"""
    
    def __init__(self, is_pooled: bool = False):
        self.is_pooled = is_pooled
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = time.time() - self.start_time
            record_db_query_time(duration, self.is_pooled)
