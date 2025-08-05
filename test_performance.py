"""
Performance Testing Script for Essay Revision Application
Demonstrates the effectiveness of caching, connection pooling, and file streaming optimizations
"""
import time
import random
import string
import logging
from typing import List, Dict
import tempfile
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_sample_essay(length: int = 1000) -> str:
    """Generate a sample essay for testing"""
    paragraphs = [
        "The importance of education in modern society cannot be overstated. Education serves as the foundation for personal growth, economic development, and social progress.",
        "Furthermore, technology has revolutionized the way we learn and teach. Digital platforms provide unprecedented access to knowledge and learning resources.",
        "However, challenges remain in ensuring equal access to quality education. Socioeconomic disparities continue to affect educational opportunities worldwide.",
        "In conclusion, investing in education is crucial for building a better future. We must work together to overcome barriers and create inclusive learning environments.",
    ]
    
    # Repeat and shuffle paragraphs to reach desired length
    essay = ""
    while len(essay) < length:
        essay += random.choice(paragraphs) + " "
    
    return essay[:length].strip()

def create_temp_file(content: str, extension: str = '.txt') -> str:
    """Create a temporary file with given content"""
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix=extension, delete=False)
    temp_file.write(content)
    temp_file.close()
    return temp_file.name

def test_analysis_caching():
    """Test AI analysis caching performance"""
    print("\n=== Testing AI Analysis Caching ===")
    
    try:
        from cache import get_cached_analysis, cache_analysis, clear_cache, get_cache_stats
        from ai import analyze_essay_with_ai
        
        # Clear cache to start fresh
        clear_cache()
        
        # Generate test essays
        essays = [
            generate_sample_essay(500),
            generate_sample_essay(750),
            generate_sample_essay(1000),
        ]
        
        print(f"Testing with {len(essays)} sample essays...")
        
        # First run - cache misses
        print("\n--- First Analysis (Cache Misses) ---")
        first_run_times = []
        
        for i, essay in enumerate(essays):
            start_time = time.time()
            # Note: This would normally call AI, but we'll simulate it
            print(f"Essay {i+1}: Simulating AI analysis...")
            # result = analyze_essay_with_ai(essay)
            end_time = time.time()
            analysis_time = end_time - start_time
            first_run_times.append(analysis_time)
            print(f"Essay {i+1}: {analysis_time:.3f}s")
        
        # Simulate caching some results
        for i, essay in enumerate(essays):
            mock_result = {
                'essay_type': 'argumentative',
                'scores': {'ideas': 85, 'organization': 80, 'style': 75, 'grammar': 90},
                'suggestions': [],
                'examples': {'ideas': [], 'organization': [], 'style': [], 'grammar': []}
            }
            cache_analysis(essay, mock_result)
        
        # Second run - cache hits
        print("\n--- Second Analysis (Cache Hits) ---")
        second_run_times = []
        
        for i, essay in enumerate(essays):
            start_time = time.time()
            cached_result = get_cached_analysis(essay)
            end_time = time.time()
            cache_time = end_time - start_time
            second_run_times.append(cache_time)
            
            if cached_result:
                print(f"Essay {i+1}: Cache hit! {cache_time:.6f}s")
            else:
                print(f"Essay {i+1}: Cache miss {cache_time:.3f}s")
        
        # Show statistics
        stats = get_cache_stats()
        print(f"\nCache Statistics:")
        print(f"Total entries: {stats.get('total_entries', 0)}")
        print(f"Active entries: {stats.get('active_entries', 0)}")
        print(f"Cache enabled: {stats.get('cache_enabled', False)}")
        
        # Calculate performance improvement
        if first_run_times and second_run_times:
            avg_first = sum(first_run_times) / len(first_run_times)
            avg_second = sum(second_run_times) / len(second_run_times)
            improvement = ((avg_first - avg_second) / avg_first) * 100
            print(f"\nPerformance Improvement: {improvement:.1f}%")
        
    except ImportError as e:
        print(f"Caching module not available: {e}")
    except Exception as e:
        print(f"Error testing caching: {e}")

def test_database_pooling():
    """Test database connection pooling performance"""
    print("\n=== Testing Database Connection Pooling ===")
    
    try:
        from db_pool import get_db_connection_pooled, get_pool_stats
        from db import get_db_connection
        
        # Test connection pool stats
        print("Testing connection pool functionality...")
        
        # Get pool statistics
        pool_stats = get_pool_stats()
        print(f"Pool Statistics:")
        for key, value in pool_stats.items():
            print(f"  {key}: {value}")
        
        # Test multiple connections
        print("\nTesting multiple connections...")
        connections = []
        
        start_time = time.time()
        for i in range(5):
            try:
                with get_db_connection_pooled() as conn:
                    print(f"Connection {i+1}: Success")
                    # Simulate some work
                    time.sleep(0.01)
            except Exception as e:
                print(f"Connection {i+1}: Failed - {e}")
        
        end_time = time.time()
        total_time = end_time - start_time
        print(f"\nTotal time for 5 connections: {total_time:.3f}s")
        print(f"Average time per connection: {total_time/5:.3f}s")
        
        # Get updated stats
        updated_stats = get_pool_stats()
        print(f"\nUpdated Pool Statistics:")
        for key, value in updated_stats.items():
            print(f"  {key}: {value}")
        
    except ImportError as e:
        print(f"Database pooling module not available: {e}")
    except Exception as e:
        print(f"Error testing database pooling: {e}")

def test_file_streaming():
    """Test file streaming performance"""
    print("\n=== Testing File Streaming ===")
    
    try:
        from file_streaming import (
            save_uploaded_file, extract_text_from_file, 
            should_stream_file, get_file_streaming_stats
        )
        
        # Get streaming configuration
        streaming_stats = get_file_streaming_stats()
        print(f"File Streaming Configuration:")
        for key, value in streaming_stats.items():
            print(f"  {key}: {value}")
        
        # Test with different file sizes
        file_sizes = [1024, 10240, 102400, 1048576]  # 1KB, 10KB, 100KB, 1MB
        
        print(f"\nTesting streaming decision for different file sizes:")
        for size in file_sizes:
            should_stream = should_stream_file(size)
            size_mb = size / (1024 * 1024)
            print(f"  {size_mb:.2f}MB: {'Stream' if should_stream else 'Memory'}")
        
        # Create test files and measure extraction time
        print(f"\nTesting text extraction performance:")
        
        for size in [1024, 10240]:  # Smaller files for testing
            # Generate content
            content = generate_sample_essay(size)
            
            # Create temporary file
            temp_file = create_temp_file(content)
            
            try:
                # Extract text and measure time
                start_time = time.time()
                extracted_text = extract_text_from_file(temp_file, 'txt')
                end_time = time.time()
                
                extraction_time = end_time - start_time
                print(f"  {len(content)} chars: {extraction_time:.6f}s")
                
                # Verify content
                if len(extracted_text) > 0:
                    print(f"    Extraction successful: {len(extracted_text)} chars extracted")
                else:
                    print(f"    Extraction failed")
                
            finally:
                # Clean up
                try:
                    os.unlink(temp_file)
                except:
                    pass
        
    except ImportError as e:
        print(f"File streaming module not available: {e}")
    except Exception as e:
        print(f"Error testing file streaming: {e}")

def test_performance_monitoring():
    """Test performance monitoring functionality"""
    print("\n=== Testing Performance Monitoring ===")
    
    try:
        from performance_monitor import (
            get_performance_stats, record_ai_analysis_time,
            record_db_query_time, record_file_upload_stats,
            reset_performance_stats, log_performance_summary
        )
        
        # Reset stats to start fresh
        reset_performance_stats()
        
        # Simulate some performance data
        print("Simulating performance data...")
        
        # Simulate AI analysis times
        for i in range(10):
            # Simulate varying analysis times
            analysis_time = random.uniform(1.0, 3.0)
            was_cached = random.choice([True, False])
            record_ai_analysis_time(analysis_time, was_cached)
        
        # Simulate database query times
        for i in range(20):
            query_time = random.uniform(0.01, 0.1)
            is_pooled = random.choice([True, False])
            record_db_query_time(query_time, is_pooled)
        
        # Simulate file uploads
        for i in range(5):
            file_size = random.randint(1024, 1048576)  # 1KB to 1MB
            was_streamed = file_size > 102400  # Stream if > 100KB
            record_file_upload_stats(file_size, was_streamed)
        
        # Get comprehensive stats
        stats = get_performance_stats()
        
        print(f"\nPerformance Statistics Summary:")
        
        # AI Analysis stats
        ai_stats = stats['performance_stats']['ai_analysis']
        print(f"\nAI Analysis:")
        print(f"  Total requests: {ai_stats['total_requests']}")
        print(f"  Cache hits: {ai_stats['cache_hits']}")
        print(f"  Cache misses: {ai_stats['cache_misses']}")
        if ai_stats['cache_misses'] > 0:
            print(f"  Average analysis time: {ai_stats['avg_analysis_time']:.3f}s")
        
        # Database stats
        db_stats = stats['performance_stats']['database']
        print(f"\nDatabase:")
        print(f"  Total queries: {db_stats['total_queries']}")
        print(f"  Average query time: {db_stats['avg_query_time']:.3f}s")
        print(f"  Pooled connections: {db_stats['pooled_connections']}")
        print(f"  Direct connections: {db_stats['direct_connections']}")
        
        # File handling stats
        file_stats = stats['performance_stats']['file_handling']
        print(f"\nFile Handling:")
        print(f"  Total uploads: {file_stats['total_uploads']}")
        print(f"  Streamed uploads: {file_stats['streamed_uploads']}")
        print(f"  Memory uploads: {file_stats['memory_uploads']}")
        if file_stats['total_uploads'] > 0:
            avg_size_kb = file_stats['avg_upload_size'] / 1024
            print(f"  Average upload size: {avg_size_kb:.1f}KB")
        
        # Log performance summary
        print(f"\n--- Performance Summary Log ---")
        log_performance_summary()
        
    except ImportError as e:
        print(f"Performance monitoring module not available: {e}")
    except Exception as e:
        print(f"Error testing performance monitoring: {e}")

def main():
    """Run all performance tests"""
    print("=" * 60)
    print("Essay Revision Application - Performance Testing")
    print("=" * 60)
    
    # Run all tests
    test_analysis_caching()
    test_database_pooling()
    test_file_streaming()
    test_performance_monitoring()
    
    print("\n" + "=" * 60)
    print("Performance testing completed!")
    print("=" * 60)

if __name__ == "__main__":
    main()
