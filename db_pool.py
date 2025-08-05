"""
Database connection pool module for the Essay Revision Application
Provides connection pooling to improve database performance under high load
"""
import pymysql
import threading
import time
import logging
from queue import Queue, Empty, Full
from contextlib import contextmanager
from typing import Optional
from config import Config

logger = logging.getLogger(__name__)

class DatabaseConnectionPool:
    """
    Database connection pool implementation using PyMySQL
    """
    
    def __init__(self, 
                 pool_size: int = 10,
                 max_overflow: int = 20,
                 timeout: int = 30,
                 recycle_time: int = 3600):
        """
        Initialize database connection pool
        
        Args:
            pool_size (int): Number of connections to maintain in pool
            max_overflow (int): Additional connections beyond pool_size
            timeout (int): Timeout for getting connection from pool
            recycle_time (int): Time after which connections are recycled
        """
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.timeout = timeout
        self.recycle_time = recycle_time
        
        # Thread-safe queue for connections
        self._pool = Queue(maxsize=pool_size)
        self._overflow_connections = set()
        self._connection_timestamps = {}
        self._lock = threading.RLock()
        
        # Pool statistics
        self._created_connections = 0
        self._active_connections = 0
        self._pool_hits = 0
        self._pool_misses = 0
        
        # Initialize the pool
        self._initialize_pool()
    
    def _create_connection(self) -> pymysql.Connection:
        """
        Create a new database connection
        
        Returns:
            pymysql.Connection: New database connection
        """
        try:
            connection = pymysql.connect(**Config.DB_CONFIG)
            self._created_connections += 1
            self._connection_timestamps[id(connection)] = time.time()
            logger.debug(f"Created new database connection (total: {self._created_connections})")
            return connection
        except Exception as e:
            logger.error(f"Failed to create database connection: {e}")
            raise
    
    def _initialize_pool(self):
        """Initialize the connection pool with initial connections"""
        try:
            for _ in range(self.pool_size):
                connection = self._create_connection()
                self._pool.put_nowait(connection)
            logger.info(f"Initialized database connection pool with {self.pool_size} connections")
        except Exception as e:
            logger.error(f"Failed to initialize connection pool: {e}")
            raise
    
    def _is_connection_expired(self, connection: pymysql.Connection) -> bool:
        """
        Check if a connection should be recycled
        
        Args:
            connection (pymysql.Connection): Connection to check
            
        Returns:
            bool: True if connection should be recycled
        """
        conn_id = id(connection)
        if conn_id not in self._connection_timestamps:
            return True
        
        age = time.time() - self._connection_timestamps[conn_id]
        return age > self.recycle_time
    
    def _validate_connection(self, connection: pymysql.Connection) -> bool:
        """
        Validate that a connection is still usable
        
        Args:
            connection (pymysql.Connection): Connection to validate
            
        Returns:
            bool: True if connection is valid
        """
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            return True
        except Exception:
            return False
    
    def get_connection(self) -> pymysql.Connection:
        """
        Get a connection from the pool
        
        Returns:
            pymysql.Connection: Database connection
            
        Raises:
            Exception: If unable to get connection within timeout
        """
        with self._lock:
            self._active_connections += 1
        
        # Try to get connection from pool
        try:
            connection = self._pool.get_nowait()
            
            # Check if connection needs to be recycled or is invalid
            if self._is_connection_expired(connection) or not self._validate_connection(connection):
                try:
                    connection.close()
                except:
                    pass
                
                # Create new connection
                connection = self._create_connection()
                self._pool_misses += 1
            else:
                self._pool_hits += 1
            
            logger.debug("Retrieved connection from pool")
            return connection
            
        except Empty:
            # Pool is empty, check if we can create overflow connection
            with self._lock:
                if len(self._overflow_connections) < self.max_overflow:
                    connection = self._create_connection()
                    self._overflow_connections.add(id(connection))
                    self._pool_misses += 1
                    logger.debug("Created overflow connection")
                    return connection
            
            # Wait for a connection to become available
            try:
                connection = self._pool.get(timeout=self.timeout)
                
                # Validate the connection
                if not self._validate_connection(connection):
                    connection = self._create_connection()
                
                self._pool_hits += 1
                logger.debug("Retrieved connection from pool after waiting")
                return connection
                
            except Empty:
                with self._lock:
                    self._active_connections -= 1
                raise Exception(f"Unable to get database connection within {self.timeout} seconds")
    
    def return_connection(self, connection: pymysql.Connection):
        """
        Return a connection to the pool
        
        Args:
            connection (pymysql.Connection): Connection to return
        """
        with self._lock:
            self._active_connections -= 1
        
        try:
            conn_id = id(connection)
            
            # Check if this is an overflow connection
            if conn_id in self._overflow_connections:
                self._overflow_connections.remove(conn_id)
                connection.close()
                logger.debug("Closed overflow connection")
                return
            
            # Check if connection should be recycled
            if self._is_connection_expired(connection) or not self._validate_connection(connection):
                try:
                    connection.close()
                except:
                    pass
                
                # Replace with new connection
                try:
                    new_connection = self._create_connection()
                    self._pool.put_nowait(new_connection)
                    logger.debug("Recycled expired/invalid connection")
                except Full:
                    # Pool is full, just close the new connection
                    new_connection.close()
                return
            
            # Return connection to pool
            try:
                self._pool.put_nowait(connection)
                logger.debug("Returned connection to pool")
            except Full:
                # Pool is full, close the connection
                connection.close()
                logger.debug("Pool full, closed returned connection")
                
        except Exception as e:
            logger.error(f"Error returning connection to pool: {e}")
            try:
                connection.close()
            except:
                pass
    
    @contextmanager
    def get_connection_context(self):
        """
        Context manager for getting and returning connections
        
        Usage:
            with pool.get_connection_context() as connection:
                # Use connection
                pass
        """
        connection = self.get_connection()
        try:
            yield connection
        finally:
            self.return_connection(connection)
    
    def close_all(self):
        """Close all connections in the pool"""
        with self._lock:
            # Close all connections in the pool
            while not self._pool.empty():
                try:
                    connection = self._pool.get_nowait()
                    connection.close()
                except:
                    pass
            
            # Close overflow connections
            # Note: We can't directly close overflow connections as they might be in use
            # They will be closed when returned to the pool
            
            logger.info("Closed all connections in pool")
    
    def get_stats(self) -> dict:
        """
        Get pool statistics
        
        Returns:
            dict: Pool statistics
        """
        return {
            'pool_size': self.pool_size,
            'max_overflow': self.max_overflow,
            'active_connections': self._active_connections,
            'pool_connections': self._pool.qsize(),
            'overflow_connections': len(self._overflow_connections),
            'created_connections': self._created_connections,
            'pool_hits': self._pool_hits,
            'pool_misses': self._pool_misses,
            'hit_ratio': self._pool_hits / (self._pool_hits + self._pool_misses) if (self._pool_hits + self._pool_misses) > 0 else 0
        }

# Global connection pool instance
_connection_pool: Optional[DatabaseConnectionPool] = None
_pool_lock = threading.Lock()

def get_connection_pool() -> DatabaseConnectionPool:
    """
    Get the global connection pool instance (singleton pattern)
    
    Returns:
        DatabaseConnectionPool: Global connection pool
    """
    global _connection_pool
    
    if _connection_pool is None:
        with _pool_lock:
            if _connection_pool is None:
                performance_config = Config.PERFORMANCE
                _connection_pool = DatabaseConnectionPool(
                    pool_size=performance_config.get('db_pool_size', 10),
                    max_overflow=performance_config.get('db_pool_max_overflow', 20),
                    timeout=performance_config.get('db_pool_timeout', 30),
                    recycle_time=performance_config.get('db_pool_recycle', 3600)
                )
    
    return _connection_pool

def get_pooled_connection() -> pymysql.Connection:
    """
    Get a connection from the pool
    
    Returns:
        pymysql.Connection: Database connection
    """
    if Config.PERFORMANCE.get('db_pool_enabled', True):
        pool = get_connection_pool()
        return pool.get_connection()
    else:
        # Fall back to direct connection
        return pymysql.connect(**Config.DB_CONFIG)

def return_pooled_connection(connection: pymysql.Connection):
    """
    Return a connection to the pool
    
    Args:
        connection (pymysql.Connection): Connection to return
    """
    if Config.PERFORMANCE.get('db_pool_enabled', True):
        pool = get_connection_pool()
        pool.return_connection(connection)
    else:
        # Direct connection, just close it
        try:
            connection.close()
        except:
            pass

@contextmanager
def get_db_connection_pooled():
    """
    Context manager for getting and returning pooled connections
    
    Usage:
        with get_db_connection_pooled() as connection:
            # Use connection
            pass
    """
    if Config.PERFORMANCE.get('db_pool_enabled', True):
        pool = get_connection_pool()
        with pool.get_connection_context() as connection:
            yield connection
    else:
        # Fall back to direct connection
        connection = pymysql.connect(**Config.DB_CONFIG)
        try:
            yield connection
        finally:
            try:
                connection.close()
            except:
                pass

def get_pool_stats() -> dict:
    """
    Get connection pool statistics
    
    Returns:
        dict: Pool statistics
    """
    if Config.PERFORMANCE.get('db_pool_enabled', True):
        pool = get_connection_pool()
        return pool.get_stats()
    else:
        return {'pool_enabled': False}

def close_connection_pool():
    """Close the connection pool"""
    global _connection_pool
    
    if _connection_pool is not None:
        with _pool_lock:
            if _connection_pool is not None:
                _connection_pool.close_all()
                _connection_pool = None
                logger.info("Connection pool closed")
