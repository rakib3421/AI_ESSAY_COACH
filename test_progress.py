import pymysql
from config import Config

def test_progress_queries():
    conn = pymysql.connect(**Config.DB_CONFIG)
    cursor = conn.cursor()
    
    print("Testing progress queries...")
    
    # Test essays query with a specific student
    print("\n1. Testing essays query:")
    cursor.execute("""
        SELECT ss.student_id, ea.id, ea.essay_type, ea.ideas_score, 
               ea.organization_score, ea.style_score, ea.grammar_score, 
               ea.overall_score, ea.created_at
        FROM student_submissions ss
        JOIN essay_analyses ea ON ss.analysis_id = ea.id
        WHERE ea.overall_score IS NOT NULL
        ORDER BY ea.created_at
    """)
    essays = cursor.fetchall()
    print(f"Found {len(essays)} essays with scores")
    
    if essays:
        print("Sample essay data:")
        for i, essay in enumerate(essays[:3]):
            print(f"  Essay {i+1}: Student={essay[0]}, ID={essay[1]}, Type={essay[2]}, Scores={essay[3:7]}, Total={essay[7]}")
    
    # Test progress data query
    print("\n2. Testing progress data query:")
    cursor.execute("""
        SELECT ss.student_id, DATE(ea.created_at) as date, AVG(ea.overall_score) as avg_score
        FROM student_submissions ss
        JOIN essay_analyses ea ON ss.analysis_id = ea.id
        WHERE ea.overall_score IS NOT NULL
        GROUP BY ss.student_id, DATE(ea.created_at)
        ORDER BY ss.student_id, date
    """)
    progress_data = cursor.fetchall()
    print(f"Found {len(progress_data)} progress data points")
    
    if progress_data:
        print("Sample progress data:")
        for i, data in enumerate(progress_data[:5]):
            print(f"  Point {i+1}: Student={data[0]}, Date={data[1]}, Score={data[2]}")
    
    # Test for a specific student
    print("\n3. Testing for specific student (student_id=1):")
    cursor.execute("""
        SELECT ea.id, 'Untitled Essay' as title, ea.essay_type, ea.ideas_score, 
               ea.organization_score, ea.style_score, ea.grammar_score, 
               ea.overall_score as total_score, ea.created_at
        FROM student_submissions ss
        JOIN essay_analyses ea ON ss.analysis_id = ea.id
        WHERE ss.student_id = %s AND ea.overall_score IS NOT NULL
        ORDER BY ea.created_at
    """, (1,))
    student_essays = cursor.fetchall()
    print(f"Found {len(student_essays)} essays for student 1")
    
    cursor.execute("""
        SELECT DATE(ea.created_at) as date, AVG(ea.overall_score) as avg_score
        FROM student_submissions ss
        JOIN essay_analyses ea ON ss.analysis_id = ea.id
        WHERE ss.student_id = %s AND ea.overall_score IS NOT NULL
        GROUP BY DATE(ea.created_at)
        ORDER BY date
    """, (1,))
    student_progress = cursor.fetchall()
    print(f"Found {len(student_progress)} progress points for student 1")
    
    conn.close()

if __name__ == "__main__":
    test_progress_queries()
