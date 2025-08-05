"""
Script to fix essay_type data truncation issues
This script normalizes all essay_type values in the database
"""
import pymysql
from config import Config
from ai import normalize_essay_type

def fix_essay_types():
    """Fix essay_type values in all relevant tables"""
    conn = pymysql.connect(**Config.DB_CONFIG)
    cursor = conn.cursor()
    
    print("Starting essay_type normalization...")
    
    # Fix essay_analyses table
    print("1. Fixing essay_analyses table...")
    cursor.execute("SELECT id, essay_type FROM essay_analyses WHERE essay_type IS NOT NULL")
    analyses = cursor.fetchall()
    
    fixed_analyses = 0
    for analysis_id, essay_type in analyses:
        normalized_type = normalize_essay_type(essay_type)
        if normalized_type != essay_type:
            cursor.execute(
                "UPDATE essay_analyses SET essay_type = %s WHERE id = %s",
                (normalized_type, analysis_id)
            )
            fixed_analyses += 1
    
    print(f"   - Fixed {fixed_analyses} essay analyses")
    
    # Fix essays table
    print("2. Fixing essays table...")
    cursor.execute("SELECT id, essay_type FROM essays WHERE essay_type IS NOT NULL")
    essays = cursor.fetchall()
    
    fixed_essays = 0
    for essay_id, essay_type in essays:
        normalized_type = normalize_essay_type(essay_type)
        if normalized_type != essay_type:
            cursor.execute(
                "UPDATE essays SET essay_type = %s WHERE id = %s",
                (normalized_type, essay_id)
            )
            fixed_essays += 1
    
    print(f"   - Fixed {fixed_essays} essays")
    
    # Fix assignments table
    print("3. Fixing assignments table...")
    cursor.execute("SELECT id, essay_type FROM assignments WHERE essay_type IS NOT NULL AND essay_type != 'auto'")
    assignments = cursor.fetchall()
    
    fixed_assignments = 0
    for assignment_id, essay_type in assignments:
        normalized_type = normalize_essay_type(essay_type)
        if normalized_type != essay_type:
            cursor.execute(
                "UPDATE assignments SET essay_type = %s WHERE id = %s",
                (normalized_type, assignment_id)
            )
            fixed_assignments += 1
    
    print(f"   - Fixed {fixed_assignments} assignments")
    
    # Commit all changes
    conn.commit()
    
    print(f"\nDatabase normalization complete!")
    print(f"Total fixed records: {fixed_analyses + fixed_essays + fixed_assignments}")
    
    # Show current essay type distribution
    print("\nCurrent essay type distribution:")
    cursor.execute("""
        SELECT essay_type, COUNT(*) as count 
        FROM essay_analyses 
        WHERE essay_type IS NOT NULL 
        GROUP BY essay_type
    """)
    
    for essay_type, count in cursor.fetchall():
        print(f"   - {essay_type}: {count}")
    
    cursor.close()
    conn.close()

if __name__ == '__main__':
    fix_essay_types()
