"""
Database module for the Essay Revision Application
Contains all database-related functions and operations
"""
import pymysql
import json
import datetime
import logging
import time
from config import Config

logger = logging.getLogger(__name__)

def get_db_connection(max_retries=3, retry_delay=1):
    """
    Get database connection with retry logic and comprehensive error handling
    
    Args:
        max_retries (int): Maximum number of connection attempts
        retry_delay (int): Delay between retry attempts in seconds
    
    Returns:
        pymysql.Connection or None: Database connection object or None if failed
    """
    for attempt in range(max_retries):
        try:
            connection = pymysql.connect(**Config.DB_CONFIG)
            # Test the connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            logger.info(f"Database connection established successfully on attempt {attempt + 1}")
            return connection
        
        except pymysql.Error as e:
            error_code = e.args[0] if e.args else 'Unknown'
            error_msg = e.args[1] if len(e.args) > 1 else str(e)
            
            # Specific error handling
            if error_code == 1049:  # Unknown database
                logger.error(f"Database '{Config.DB_CONFIG.get('database')}' does not exist")
                return None
            elif error_code == 1045:  # Access denied
                logger.error(f"Access denied for user '{Config.DB_CONFIG.get('user')}' - check credentials")
                return None
            elif error_code == 2003:  # Can't connect to server
                logger.warning(f"Cannot connect to database server at {Config.DB_CONFIG.get('host')} (attempt {attempt + 1}/{max_retries})")
            elif error_code == 1040:  # Too many connections
                logger.warning(f"Too many database connections (attempt {attempt + 1}/{max_retries})")
            else:
                logger.warning(f"Database connection failed: {error_code} - {error_msg} (attempt {attempt + 1}/{max_retries})")
            
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                logger.error(f"All {max_retries} database connection attempts failed")
                return None
        
        except Exception as e:
            logger.error(f"Unexpected error during database connection: {e} (attempt {attempt + 1}/{max_retries})")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                retry_delay *= 2
            else:
                return None
    
    return None

def save_analysis_to_db(essay_text, analysis_data):
    """
    Save essay analysis to database with comprehensive error handling
    
    Args:
        essay_text (str): The essay text
        analysis_data (dict): Analysis results from AI
    
    Returns:
        int or False: Analysis ID if successful, False if failed
    """
    connection = get_db_connection()
    if not connection:
        logger.error("Database connection failed, cannot save analysis")
        return False
    
    try:
        with connection.cursor() as cursor:
            # Save essay analysis
            sql = """
            INSERT INTO essay_analyses (essay_text, essay_type, ideas_score, 
                                     organization_score, style_score, grammar_score, 
                                     overall_score, suggestions, word_suggestions, vocabulary_score, clarity_score, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            overall_score = sum(analysis_data['scores'].values()) // 4
            
            cursor.execute(sql, (
                essay_text,
                analysis_data['essay_type'],
                analysis_data['scores']['ideas'],
                analysis_data['scores']['organization'],
                analysis_data['scores']['style'],
                analysis_data['scores']['grammar'],
                overall_score,
                json.dumps(analysis_data.get('suggestions', [])),
                json.dumps(analysis_data.get('word_suggestions', [])),
                analysis_data.get('scores', {}).get('vocabulary', 0),
                analysis_data.get('scores', {}).get('clarity', 0),
                datetime.datetime.now()
            ))
            analysis_id = cursor.lastrowid
            analysis_data['analysis_id'] = analysis_id  # Add analysis_id to the data

            # Save examples in a separate table
            for dimension in ['ideas', 'organization', 'style', 'grammar']:
                examples = analysis_data.get('examples', {}).get(dimension, [])
                if examples and len(examples) > 0:
                    for example_text in examples[:2]:  # Limit to 2 examples
                        try:
                            cursor.execute("""
                            INSERT INTO rubric_examples (analysis_id, dimension, example_text, created_at)
                            VALUES (%s, %s, %s, %s)
                            """, (analysis_id, dimension, example_text, datetime.datetime.now()))
                        except Exception as e:
                            logger.warning(f"Failed to save example for dimension {dimension}: {e}")

            connection.commit()

            # Save checklist progress if provided
            checklist_progress = analysis_data.get('checklist_progress')
            student_id = analysis_data.get('student_id')
            submission_id = analysis_data.get('submission_id')
            if checklist_progress and student_id and submission_id:
                for step, completed in checklist_progress.items():
                    try:
                        cursor.execute("""
                            INSERT INTO checklist_progress (student_id, submission_id, step_name, completed, updated_at)
                            VALUES (%s, %s, %s, %s, NOW())
                            ON DUPLICATE KEY UPDATE completed = VALUES(completed), updated_at = VALUES(updated_at)
                        """, (student_id, submission_id, step, bool(completed)))
                    except Exception as e:
                        logger.warning(f"Failed to save checklist progress for step {step}: {e}")
                
                try:
                    connection.commit()
                except Exception as e:
                    logger.warning(f"Failed to commit checklist progress: {e}")

            logger.info("Analysis and examples saved to database successfully")
            return analysis_id
    
    except pymysql.Error as e:
        error_code = e.args[0] if e.args else 'Unknown'
        error_msg = e.args[1] if len(e.args) > 1 else str(e)
        logger.error(f"Database error while saving analysis: {error_code} - {error_msg}")
        
        # Try to rollback
        try:
            connection.rollback()
        except:
            pass
        return False
    
    except KeyError as e:
        logger.error(f"Missing required data in analysis_data: {e}")
        return False
    
    except Exception as e:
        logger.error(f"Unexpected error while saving analysis: {e}")
        try:
            connection.rollback()
        except:
            pass
        return False
    
    finally:
        try:
            connection.close()
        except:
            pass

def save_submission_to_db(student_id, analysis_id, assignment_id=None):
    """
    Save student submission to database with error handling
    
    Args:
        student_id (int): Student ID
        analysis_id (int): Analysis ID
        assignment_id (int, optional): Assignment ID
    
    Returns:
        bool: True if successful, False if failed
    """
    connection = get_db_connection()
    if not connection:
        logger.error("Database connection failed, cannot save submission")
        return False
    
    try:
        with connection.cursor() as cursor:
            sql = """
            INSERT INTO student_submissions (student_id, analysis_id, assignment_id, submitted_at)
            VALUES (%s, %s, %s, %s)
            """
            cursor.execute(sql, (student_id, analysis_id, assignment_id, datetime.datetime.now()))
            connection.commit()
            logger.info(f"Submission saved successfully for student {student_id}")
            return True
    
    except pymysql.Error as e:
        error_code = e.args[0] if e.args else 'Unknown'
        error_msg = e.args[1] if len(e.args) > 1 else str(e)
        logger.error(f"Database error while saving submission: {error_code} - {error_msg}")
        return False
    
    except Exception as e:
        logger.error(f"Unexpected error while saving submission: {e}")
        return False
    
    finally:
        try:
            connection.close()
        except:
            pass

def save_step_wise_checklist(analysis_id, steps):
    """Save step-wise checklist to database"""
    connection = get_db_connection()
    if not connection:
        return False
    
    try:
        with connection.cursor() as cursor:
            for step in steps:
                cursor.execute("""
                    INSERT INTO step_wise_checklists 
                    (analysis_id, step_name, step_description, step_order, is_required, 
                     completion_criteria, is_completed, unlocked)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    analysis_id,
                    step['name'],
                    step['description'],
                    step['order'],
                    step['required'],
                    step['criteria'],
                    step['completed'],
                    step['unlocked']
                ))
            connection.commit()
            return True
    except Exception as e:
        logger.error(f"Error saving step-wise checklist: {e}")
        return False
    finally:
        connection.close()

def update_checklist_progress(analysis_id, step_name, completed=True):
    """Update checklist step completion and unlock next step if applicable"""
    connection = get_db_connection()
    if not connection:
        return False
    
    try:
        with connection.cursor() as cursor:
            # Mark current step as completed
            cursor.execute("""
                UPDATE step_wise_checklists 
                SET is_completed = %s 
                WHERE analysis_id = %s AND step_name = %s
            """, (completed, analysis_id, step_name))
            
            if completed:
                # Get current step order
                cursor.execute("""
                    SELECT step_order FROM step_wise_checklists 
                    WHERE analysis_id = %s AND step_name = %s
                """, (analysis_id, step_name))
                result = cursor.fetchone()
                
                if result:
                    current_order = result[0]
                    # Unlock next step
                    cursor.execute("""
                        UPDATE step_wise_checklists 
                        SET unlocked = TRUE 
                        WHERE analysis_id = %s AND step_order = %s
                    """, (analysis_id, current_order + 1))
            
            connection.commit()
            return True
    except Exception as e:
        logger.error(f"Error updating checklist progress: {e}")
        return False
    finally:
        connection.close()

def get_checklist_progress(analysis_id):
    """Get current checklist progress for an analysis"""
    connection = get_db_connection()
    if not connection:
        return []
    
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT step_name, step_description, step_order, is_required,
                       completion_criteria, is_completed, unlocked
                FROM step_wise_checklists
                WHERE analysis_id = %s
                ORDER BY step_order
            """, (analysis_id,))
            
            steps = []
            for row in cursor.fetchall():
                steps.append({
                    'name': row[0],
                    'description': row[1],
                    'order': row[2],
                    'required': row[3],
                    'criteria': row[4],
                    'completed': row[5],
                    'unlocked': row[6]
                })
            return steps
    except Exception as e:
        logger.error(f"Error getting checklist progress: {e}")
        return []
    finally:
        connection.close()

def create_modular_rubric_engine(teacher_id, rubric_name, weights, custom_criteria=None):
    """Create a custom rubric configuration"""
    connection = get_db_connection()
    if not connection:
        return False
    
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO rubric_configurations 
                (teacher_id, name, ideas_weight, organization_weight, style_weight, 
                 grammar_weight, custom_criteria)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                teacher_id, rubric_name, weights['ideas'], weights['organization'],
                weights['style'], weights['grammar'], json.dumps(custom_criteria or {})
            ))
            connection.commit()
            return cursor.lastrowid
    except Exception as e:
        logger.error(f"Error creating rubric configuration: {e}")
        return False
    finally:
        connection.close()
