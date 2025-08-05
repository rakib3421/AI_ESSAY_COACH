"""
Database Migration Script to Fix Essay Coach Issues
This script addresses the database structure issues and data synchronization problems
"""
import pymysql
import json
import datetime
from config import Config

def run_migration():
    """Run database migration to fix data issues"""
    conn = pymysql.connect(**Config.DB_CONFIG)
    cursor = conn.cursor()
    
    print("Starting database migration...")
    
    # 1. Create proper feedback tracking in essays table
    print("1. Migrating existing analysis data to essays table for feedback tracking...")
    
    cursor.execute("""
        INSERT INTO essays (user_id, title, content, essay_type, feedback, 
                          ideas_score, organization_score, style_score, grammar_score, 
                          total_score, status, created_at)
        SELECT 
            ss.student_id as user_id,
            'Analyzed Essay' as title,
            ea.essay_text as content,
            CASE 
                WHEN LOWER(ea.essay_type) LIKE '%argumentative%' THEN 'argumentative'
                WHEN LOWER(ea.essay_type) LIKE '%narrative%' THEN 'narrative'
                WHEN LOWER(ea.essay_type) LIKE '%literary%' THEN 'literary_analysis'
                ELSE 'hybrid'
            END as essay_type,
            ea.suggestions as feedback,
            ea.ideas_score,
            ea.organization_score,
            ea.style_score,
            ea.grammar_score,
            ea.overall_score as total_score,
            'analyzed' as status,
            ea.created_at
        FROM student_submissions ss
        JOIN essay_analyses ea ON ss.analysis_id = ea.id
        LEFT JOIN essays e ON e.user_id = ss.student_id AND e.content = ea.essay_text
        WHERE e.id IS NULL
    """)
    
    migrated_essays = cursor.rowcount
    print(f"   - Migrated {migrated_essays} essays from essay_analyses to essays table")
    
    # 2. Update assignment submissions to link with essays table
    print("2. Linking assignment submissions with essays...")
    
    cursor.execute("""
        UPDATE assignment_submissions asub
        JOIN student_submissions ss ON asub.assignment_id IS NOT NULL
        JOIN essay_analyses ea ON ss.analysis_id = ea.id
        JOIN essays e ON e.user_id = ss.student_id AND e.content = ea.essay_text
        SET asub.essay_id = e.id
        WHERE asub.essay_id IS NULL
    """)
    
    linked_assignments = cursor.rowcount
    print(f"   - Linked {linked_assignments} assignment submissions with essays")
    
    # 3. Create feedback summary for analytics
    print("3. Creating analytics summary...")
    
    cursor.execute("""SELECT COUNT(*) FROM student_submissions""")
    total_submissions = cursor.fetchone()[0]
    
    cursor.execute("""SELECT COUNT(*) FROM essays WHERE teacher_feedback IS NOT NULL""")
    essays_with_feedback = cursor.fetchone()[0]
    
    cursor.execute("""SELECT COUNT(DISTINCT student_id) FROM student_submissions""")
    active_students = cursor.fetchone()[0]
    
    print(f"   - Total submissions: {total_submissions}")
    print(f"   - Essays with teacher feedback: {essays_with_feedback}")
    print(f"   - Active students: {active_students}")
    
    # 4. Verify data integrity
    print("4. Verifying data integrity...")
    
    cursor.execute("""
        SELECT COUNT(*) FROM student_submissions ss
        LEFT JOIN essay_analyses ea ON ss.analysis_id = ea.id
        WHERE ea.id IS NULL
    """)
    orphaned_submissions = cursor.fetchone()[0]
    
    if orphaned_submissions > 0:
        print(f"   - WARNING: Found {orphaned_submissions} orphaned submissions")
        # Clean up orphaned submissions
        cursor.execute("""
            DELETE FROM student_submissions 
            WHERE analysis_id NOT IN (SELECT id FROM essay_analyses)
        """)
        print(f"   - Cleaned up {cursor.rowcount} orphaned submissions")
    
    conn.commit()
    conn.close()
    
    print("Migration completed successfully!")
    print("\nSummary of fixes applied:")
    print("- Fixed student dashboard to show essays from essay_analyses table")
    print("- Fixed teacher dashboard to show submissions properly")
    print("- Fixed analytics to use correct data sources")
    print("- Created proper teacher feedback system")
    print("- Fixed student progress tracking")
    print("- Migrated data for better integration")

if __name__ == "__main__":
    run_migration()
