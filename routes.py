"""
Routes module for the Essay Revision Application
Contains all Flask route definitions
"""
from flask import render_template, request, jsonify, redirect, url_for, session, flash, send_file, make_response
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import json
import datetime
import tempfile
from io import BytesIO
import logging

from utils import (
    login_required, role_required, get_current_user, allowed_file, 
    is_file_size_valid, extract_text_from_file, safe_get_string,
    create_word_document_with_suggestions, sanitize_text, validate_file_upload
)
from db import (
    get_db_connection, save_analysis_to_db, save_submission_to_db,
    get_checklist_progress, update_checklist_progress, create_modular_rubric_engine
)
from ai import analyze_essay_with_ai, generate_step_wise_checklist
from config import Config

logger = logging.getLogger(__name__)

def register_routes(app):
    """Register all routes with the Flask app"""
    
    # Configure upload folder
    app.config['UPLOAD_FOLDER'] = Config.UPLOAD_FOLDER
    app.config['MAX_CONTENT_LENGTH'] = Config.MAX_CONTENT_LENGTH
    
    # Ensure upload folder exists
    if not os.path.exists(Config.UPLOAD_FOLDER):
        os.makedirs(Config.UPLOAD_FOLDER)

    # Home and Auth Routes
    @app.route('/')
    def index():
        """Home page"""
        if 'user_id' in session:
            if session['role'] == 'student':
                return redirect(url_for('student_dashboard'))
            else:
                return redirect(url_for('teacher_dashboard'))
        return render_template('index.html')

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        """Login page"""
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id, username, password, role FROM users WHERE username = %s", (username,))
            user = cursor.fetchone()
            conn.close()
            
            if user and check_password_hash(user[2], password):
                session['user_id'] = user[0]
                session['username'] = user[1]
                session['role'] = user[3]
                
                if user[3] == 'student':
                    return redirect(url_for('student_dashboard'))
                else:
                    return redirect(url_for('teacher_dashboard'))
            else:
                flash('Invalid username or password', 'error')
        
        return render_template('login.html')

    @app.route('/signup', methods=['GET', 'POST'])
    def signup():
        """Signup page"""
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            email = request.form['email']
            role = request.form['role']
            
            # Validate input
            if not username or not password or not email or not role:
                flash('All fields are required', 'error')
                return render_template('signup.html')
            
            if role not in ['student', 'teacher']:
                flash('Invalid role selected', 'error')
                return render_template('signup.html')
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Check if username exists
            cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
            if cursor.fetchone():
                flash('Username already exists', 'error')
                conn.close()
                return render_template('signup.html')
            
            # Check if email exists
            cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
            if cursor.fetchone():
                flash('Email already exists', 'error')
                conn.close()
                return render_template('signup.html')
            
            # Create user
            hashed_password = generate_password_hash(password)
            cursor.execute(
                "INSERT INTO users (username, password, email, role, created_at) VALUES (%s, %s, %s, %s, %s)",
                (username, hashed_password, email, role, datetime.datetime.now())
            )
            conn.commit()
            
            # Get user ID
            user_id = cursor.lastrowid
            conn.close()
            
            # Set session
            session['user_id'] = user_id
            session['username'] = username
            session['role'] = role
            
            if role == 'student':
                return redirect(url_for('student_dashboard'))
            else:
                return redirect(url_for('teacher_dashboard'))
        
        return render_template('signup.html')

    @app.route('/logout')
    def logout():
        """Logout user"""
        session.clear()
        flash('Logged out successfully', 'success')
        return redirect(url_for('index'))

    # Student Routes
    @app.route('/student/dashboard')
    @login_required
    @role_required('student')
    def student_dashboard():
        """Student dashboard"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get recent submissions
        cursor.execute("""
            SELECT id, title, essay_type, status, created_at, total_score, teacher_feedback 
            FROM essays 
            WHERE user_id = %s 
            ORDER BY created_at DESC 
            LIMIT 5
        """, (session['user_id'],))
        recent_submissions = cursor.fetchall()
        
        # Get progress data
        cursor.execute("""
            SELECT AVG(ideas_score) as avg_ideas, AVG(organization_score) as avg_org, 
                   AVG(style_score) as avg_style, AVG(grammar_score) as avg_grammar
            FROM essays 
            WHERE user_id = %s AND total_score IS NOT NULL
        """, (session['user_id'],))
        progress = cursor.fetchone()
        
        # Get assignments with feedback info
        cursor.execute("""
            SELECT a.id, a.title, a.description, a.essay_type, a.due_date,
                   CASE WHEN s.id IS NOT NULL THEN 'Submitted' ELSE 'Pending' END as status,
                   s.essay_id,
                   e.teacher_feedback
            FROM assignments a
            LEFT JOIN assignment_submissions s ON a.id = s.assignment_id AND s.student_id = %s
            LEFT JOIN essays e ON s.essay_id = e.id
            WHERE a.teacher_id IN (
                SELECT teacher_id FROM student_teacher_assignments WHERE student_id = %s
            )
            ORDER BY a.due_date
        """, (session['user_id'], session['user_id']))
        assignments = cursor.fetchall()
        
        # Get pending assignment requests count
        cursor.execute("""
            SELECT COUNT(*) FROM assignment_requests 
            WHERE student_id = %s AND status = 'pending'
        """, (session['user_id'],))
        pending_requests_count = cursor.fetchone()[0]
        
        conn.close()
        
        return render_template('student/dashboard.html', 
                             submissions=recent_submissions, 
                             progress=progress, 
                             assignments=assignments,
                             pending_requests_count=pending_requests_count)

    @app.route('/student/upload', methods=['GET', 'POST'])
    @login_required
    @role_required('student')
    def upload_essay():
        """Upload essay for analysis"""
        assignment_id = request.args.get('assignment_id', type=int)
        assignment_essay_type = None
        
        # If this is for an assignment, get the assignment's essay type
        if assignment_id:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT essay_type FROM assignments WHERE id = %s", (assignment_id,))
            assignment_data = cursor.fetchone()
            conn.close()
            if assignment_data:
                assignment_essay_type = assignment_data[0]
        
        if request.method == 'POST':
            if 'file' not in request.files:
                flash('No file selected', 'error')
                return redirect(request.url)
            
            file = request.files['file']
            title = request.form['title']
            essay_type = request.form.get('essay_type', 'auto')
            coaching_level = request.form.get('coaching_level', 'medium')
            suggestion_level = request.form.get('suggestion_level', 'medium')
            
            # Get assignment_id from form if it exists (overrides URL parameter)
            form_assignment_id = request.form.get('assignment_id', type=int)
            if form_assignment_id:
                assignment_id = form_assignment_id
            
            # If this is for an assignment and the assignment has a specific type (not 'auto'), use it
            if assignment_id and assignment_essay_type and assignment_essay_type != 'auto':
                essay_type = assignment_essay_type
            
            # Comprehensive file validation
            is_valid, error_message = validate_file_upload(file)
            if not is_valid:
                flash(error_message, 'error')
                logger.warning(f"File upload validation failed for user {session['user_id']}: {error_message}")
                return redirect(request.url)
            
            try:
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                
                # Save file with error handling
                try:
                    file.save(file_path)
                except OSError as e:
                    flash('Failed to save uploaded file. Please try again.', 'error')
                    logger.error(f"Failed to save file {filename}: {e}")
                    return redirect(request.url)
                
                # Extract text from file with improved error handling
                text, extract_error = extract_text_from_file(file_path)
                if not text:
                    flash(f'Failed to process file: {extract_error}', 'error')
                    logger.warning(f"Text extraction failed for {filename}: {extract_error}")
                    try:
                        os.remove(file_path)
                    except:
                        pass
                    return redirect(request.url)
                
                # Validate extracted text
                if len(text.strip()) < 50:
                    flash('Essay is too short. Please provide at least 50 characters of text.', 'error')
                    try:
                        os.remove(file_path)
                    except:
                        pass
                    return redirect(request.url)
                
                if len(text) > 50000:  # Reasonable limit for essay analysis
                    flash('Essay is too long. Please limit to 50,000 characters.', 'error')
                    try:
                        os.remove(file_path)
                    except:
                        pass
                    return redirect(request.url)
                
                # Store analysis data and redirect to new view
                analysis_data = {
                    'essay': text,
                    'title': title,
                    'essay_type': essay_type,
                    'coaching_level': coaching_level,
                    'suggestion_aggressiveness': suggestion_level,
                    'assignment_id': assignment_id
                }
                
                # Store in session storage for the view page
                session['temp_analysis_data'] = analysis_data
                
                # Clean up uploaded file
                try:
                    os.remove(file_path)
                except Exception as e:
                    logger.warning(f"Failed to remove temporary file {file_path}: {e}")
                
                flash('Essay uploaded successfully! Analyzing with AI...', 'success')
                logger.info(f"Essay uploaded successfully by user {session['user_id']}, length: {len(text)} characters")
                return redirect(url_for('analyze_view'))
            
            except Exception as e:
                flash('An unexpected error occurred while processing your file. Please try again.', 'error')
                logger.error(f"Unexpected error in file upload for user {session['user_id']}: {e}")
                try:
                    if 'file_path' in locals() and os.path.exists(file_path):
                        os.remove(file_path)
                except:
                    pass
                return redirect(request.url)
        
        # Get assignment details to pass to template
        assignment = None
        if assignment_id:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id, title, essay_type, description FROM assignments WHERE id = %s", (assignment_id,))
            assignment = cursor.fetchone()
            conn.close()
        
        return render_template('student/upload_new.html', assignment=assignment)

    @app.route('/student/essay/<int:essay_id>')
    @login_required
    @role_required('student')
    def view_essay(essay_id):
        """View essay with AI suggestions"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, title, content, essay_type, feedback, ideas_score, 
                   organization_score, style_score, grammar_score, total_score, status
            FROM essays 
            WHERE id = %s AND user_id = %s
        """, (essay_id, session['user_id']))
        essay = cursor.fetchone()
        conn.close()
        
        if not essay:
            flash('Essay not found', 'error')
            return redirect(url_for('student_dashboard'))
        
        return render_template('student/view_essay.html', essay=essay)

    @app.route('/student/analyze-view')
    @login_required
    @role_required('student')
    def analyze_view():
        """Direct analysis view for text input"""
        # Clear temporary session data after using it
        temp_data = session.pop('temp_analysis_data', None)
        return render_template('student/view_essay_new.html', essay=None, temp_data=temp_data)

    @app.route('/student/assignments')
    @login_required
    @role_required('student')
    def view_assignments():
        """View all assignments for student"""
        try:
            conn = get_db_connection()
            if not conn:
                logger.error("Database connection failed")
                flash('Database connection error. Please try again later.', 'error')
                return redirect(url_for('student_dashboard'))
            
            cursor = conn.cursor()
            
            # First check if student has any teacher assignments
            cursor.execute("""
                SELECT COUNT(*) FROM student_teacher_assignments WHERE student_id = %s
            """, (session['user_id'],))
            teacher_count = cursor.fetchone()[0]
            
            logger.info(f"Student {session['user_id']} has {teacher_count} teacher assignments")
            
            if teacher_count == 0:
                # No teachers assigned, show all assignments for now
                cursor.execute("""
                    SELECT a.id, a.title, a.description, a.essay_type, a.due_date, a.guidelines,
                           CASE WHEN s.id IS NOT NULL THEN 'Submitted' ELSE 'Pending' END as status,
                           s.essay_id,
                           e.teacher_feedback
                    FROM assignments a
                    LEFT JOIN assignment_submissions s ON a.id = s.assignment_id AND s.student_id = %s
                    LEFT JOIN essays e ON s.essay_id = e.id
                    ORDER BY a.due_date
                """, (session['user_id'],))
            else:
                # Normal query for students with assigned teachers
                cursor.execute("""
                    SELECT a.id, a.title, a.description, a.essay_type, a.due_date, a.guidelines,
                           CASE WHEN s.id IS NOT NULL THEN 'Submitted' ELSE 'Pending' END as status,
                           s.essay_id,
                           e.teacher_feedback
                    FROM assignments a
                    LEFT JOIN assignment_submissions s ON a.id = s.assignment_id AND s.student_id = %s
                    LEFT JOIN essays e ON s.essay_id = e.id
                    WHERE a.teacher_id IN (
                        SELECT teacher_id FROM student_teacher_assignments WHERE student_id = %s
                    )
                    ORDER BY a.due_date
                """, (session['user_id'], session['user_id']))
            
            assignments = cursor.fetchall()
            logger.info(f"Found {len(assignments)} assignments for student {session['user_id']}")
            
            conn.close()
            
            return render_template('student/assignments.html', assignments=assignments)
            
        except Exception as e:
            logger.error(f"Error in view_assignments: {e}")
            flash('Error loading assignments. Please try again.', 'error')
            return redirect(url_for('student_dashboard'))

    # Teacher Routes
    @app.route('/teacher/dashboard')
    @login_required
    @role_required('teacher')
    def teacher_dashboard():
        """Teacher dashboard"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get student submissions from assigned students only
        cursor.execute("""
            SELECT e.id, e.title, e.essay_type, e.total_score, e.created_at, u.username
            FROM essays e
            JOIN users u ON e.user_id = u.id
            JOIN student_teacher_assignments sta ON u.id = sta.student_id
            WHERE u.role = 'student' AND sta.teacher_id = %s
            ORDER BY e.created_at DESC
            LIMIT 10
        """, (session['user_id'],))
        submissions = cursor.fetchall()
        
        # Get assignments created by this teacher
        cursor.execute("""
            SELECT id, title, essay_type, due_date, created_at
            FROM assignments
            WHERE teacher_id = %s
            ORDER BY created_at DESC
            LIMIT 5
        """, (session['user_id'],))
        assignments = cursor.fetchall()
        
        # Get assigned students count
        cursor.execute("""
            SELECT COUNT(*) FROM student_teacher_assignments WHERE teacher_id = %s
        """, (session['user_id'],))
        assigned_students_count = cursor.fetchone()[0]
        
        conn.close()
        
        return render_template('teacher/dashboard.html', 
                             submissions=submissions, 
                             assignments=assignments,
                             assigned_students_count=assigned_students_count)

    @app.route('/teacher/create_assignment', methods=['GET', 'POST'])
    @login_required
    @role_required('teacher')
    def create_assignment():
        """Create new assignment"""
        if request.method == 'POST':
            title = request.form['title']
            description = request.form['description']
            essay_type = request.form.get('essay_type', 'auto')
            due_date = request.form['due_date']
            guidelines = request.form['guidelines']
            
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO assignments (teacher_id, title, description, essay_type, due_date, guidelines, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (session['user_id'], title, description, essay_type, due_date, guidelines, datetime.datetime.now()))
            conn.commit()
            conn.close()
            
            flash('Assignment created successfully!', 'success')
            return redirect(url_for('teacher_dashboard'))
        
        return render_template('teacher/create_assignment.html')

    # Additional Student Routes
    @app.route('/student/progress')
    @login_required
    @role_required('student')
    def student_progress():
        """View detailed student progress"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get all essays with scores
        cursor.execute("""
            SELECT id, title, essay_type, ideas_score, organization_score, 
                   style_score, grammar_score, total_score, created_at, teacher_feedback
            FROM essays 
            WHERE user_id = %s AND total_score IS NOT NULL
            ORDER BY created_at
        """, (session['user_id'],))
        essays = cursor.fetchall()
        
        # Get progress over time
        cursor.execute("""
            SELECT DATE(created_at) as date, AVG(total_score) as avg_score
            FROM essays 
            WHERE user_id = %s AND total_score IS NOT NULL
            GROUP BY DATE(created_at)
            ORDER BY date
        """, (session['user_id'],))
        progress_data = cursor.fetchall()
        
        conn.close()
        
        return render_template('student/progress.html', essays=essays, progress_data=progress_data)

    @app.route('/student/profile', methods=['GET', 'POST'])
    @login_required
    @role_required('student')
    def student_profile():
        """Student profile page"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if request.method == 'POST':
            # Handle profile update
            username = request.form.get('username')
            email = request.form.get('email')
            
            # Update user profile
            cursor.execute("""
                UPDATE users SET username = %s, email = %s WHERE id = %s
            """, (username, email, session['user_id']))
            conn.commit()
            
            # Update session
            session['username'] = username
            
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('student_profile'))
        
        # Get current user info
        cursor.execute("""
            SELECT username, email, created_at
            FROM users WHERE id = %s
        """, (session['user_id'],))
        user_info = cursor.fetchone()
        
        conn.close()
        
        return render_template('student/profile.html', user_info=user_info)

    @app.route('/student/settings', methods=['GET', 'POST'])
    @login_required
    @role_required('student')
    def student_settings():
        """Student settings page"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if request.method == 'POST':
            # Handle settings update
            email = request.form.get('email')
            default_essay_type = request.form.get('default_essay_type', 'auto')
            coaching_level = request.form.get('coaching_level', 'medium')
            suggestion_aggressiveness = request.form.get('suggestion_aggressiveness', 'medium')
            
            # Update user settings
            cursor.execute("""
                UPDATE users SET 
                    email = %s, 
                    default_essay_type = %s, 
                    coaching_level = %s, 
                    suggestion_aggressiveness = %s 
                WHERE id = %s
            """, (email, default_essay_type, coaching_level, suggestion_aggressiveness, session['user_id']))
            conn.commit()
            
            flash('Settings updated successfully!', 'success')
            return redirect(url_for('student_settings'))
        
        # Get current user settings
        cursor.execute("""
            SELECT email, default_essay_type, coaching_level, suggestion_aggressiveness
            FROM users WHERE id = %s
        """, (session['user_id'],))
        user_settings = cursor.fetchone()
        conn.close()
        
        if not user_settings:
            flash('User not found', 'error')
            return redirect(url_for('student_dashboard'))
        
        return render_template('student/settings.html', user_settings=user_settings)

    @app.route('/student/feedback/<int:essay_id>')
    @login_required
    @role_required('student')
    def view_feedback(essay_id):
        """View teacher feedback for an essay"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get essay details including teacher feedback
        cursor.execute("""
            SELECT e.id, e.title, e.content, e.essay_type, e.feedback, e.teacher_feedback,
                   e.ideas_score, e.organization_score, e.style_score, e.grammar_score, 
                   e.total_score, e.created_at, u.username as teacher_name
            FROM essays e
            LEFT JOIN assignment_submissions asub ON e.id = asub.essay_id
            LEFT JOIN assignments a ON asub.assignment_id = a.id
            LEFT JOIN users u ON a.teacher_id = u.id
            WHERE e.id = %s AND e.user_id = %s
        """, (essay_id, session['user_id']))
        essay = cursor.fetchone()
        
        conn.close()
        
        if not essay:
            flash('Essay not found', 'error')
            return redirect(url_for('student_dashboard'))
        
        if not essay[5]:  # No teacher feedback
            flash('No teacher feedback available for this essay', 'info')
            return redirect(url_for('student_dashboard'))
        
        return render_template('student/feedback.html', essay=essay)

    @app.route('/student/requests')
    @login_required
    @role_required('student')
    def view_assignment_requests():
        """View assignment requests from teachers"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get pending requests
        cursor.execute("""
            SELECT ar.id, u.username, u.email, ar.created_at
            FROM assignment_requests ar
            JOIN users u ON ar.teacher_id = u.id
            WHERE ar.student_id = %s AND ar.status = 'pending'
            ORDER BY ar.created_at DESC
        """, (session['user_id'],))
        requests = cursor.fetchall()
        
        conn.close()
        
        return render_template('student/assignment_requests.html', requests=requests)

    @app.route('/student/submit_assignment/<int:assignment_id>')
    @login_required
    @role_required('student')
    def submit_assignment(assignment_id):
        """Submit assignment"""
        return redirect(url_for('upload_essay', assignment_id=assignment_id))

    # Additional Teacher Routes
    @app.route('/teacher/submissions')
    @login_required
    @role_required('teacher')
    def view_submissions():
        """View all student submissions from assigned students"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get all submissions from assigned students with pagination support
        cursor.execute("""
            SELECT e.id, e.title, e.essay_type, e.total_score, e.created_at, u.username, e.status
            FROM essays e
            JOIN users u ON e.user_id = u.id
            JOIN student_teacher_assignments sta ON u.id = sta.student_id
            WHERE u.role = 'student' AND sta.teacher_id = %s
            ORDER BY e.created_at DESC
            LIMIT 50
        """, (session['user_id'],))
        submissions = cursor.fetchall()
        
        conn.close()
        
        return render_template('teacher/submissions.html', submissions=submissions)

    @app.route('/teacher/assignment/<int:assignment_id>')
    @login_required
    @role_required('teacher')
    def view_assignment(assignment_id):
        """View assignment details"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get assignment details
        cursor.execute("""
            SELECT id, title, description, essay_type, due_date, guidelines, created_at
            FROM assignments
            WHERE id = %s AND teacher_id = %s
        """, (assignment_id, session['user_id']))
        assignment = cursor.fetchone()
        
        if not assignment:
            flash('Assignment not found', 'error')
            return redirect(url_for('teacher_dashboard'))
        
        # Get submission statistics
        cursor.execute("""
            SELECT COUNT(*) as total_submissions,
                   AVG(e.total_score) as avg_score
            FROM assignment_submissions asub
            JOIN essays e ON asub.essay_id = e.id
            WHERE asub.assignment_id = %s
        """, (assignment_id,))
        stats = cursor.fetchone()
        
        conn.close()
        
        return render_template('teacher/assignment_view.html', assignment=assignment, stats=stats)

    @app.route('/teacher/assignment/<int:assignment_id>/submissions')
    @login_required
    @role_required('teacher')
    def view_assignment_submissions(assignment_id):
        """View all submissions for an assignment"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get assignment details
        cursor.execute("""
            SELECT title, description, essay_type, due_date
            FROM assignments
            WHERE id = %s AND teacher_id = %s
        """, (assignment_id, session['user_id']))
        assignment = cursor.fetchone()
        
        if not assignment:
            flash('Assignment not found', 'error')
            return redirect(url_for('teacher_dashboard'))
        
        # Get all submissions for this assignment
        cursor.execute("""
            SELECT e.id, e.title, e.total_score, e.created_at, u.username, 
                   e.teacher_feedback, e.status
            FROM assignment_submissions asub
            JOIN essays e ON asub.essay_id = e.id
            JOIN users u ON e.user_id = u.id
            WHERE asub.assignment_id = %s
            ORDER BY e.created_at DESC
        """, (assignment_id,))
        submissions = cursor.fetchall()
        
        conn.close()
        
        return render_template('teacher/assignment_submissions.html', 
                             assignment=assignment, submissions=submissions, assignment_id=assignment_id)

    @app.route('/teacher/assignment/<int:assignment_id>/edit', methods=['GET', 'POST'])
    @login_required
    @role_required('teacher')
    def edit_assignment(assignment_id):
        """Edit assignment"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if request.method == 'POST':
            title = request.form['title']
            description = request.form['description']
            essay_type = request.form.get('essay_type', 'auto')
            due_date = request.form['due_date']
            guidelines = request.form['guidelines']
            
            cursor.execute("""
                UPDATE assignments 
                SET title = %s, description = %s, essay_type = %s, due_date = %s, guidelines = %s
                WHERE id = %s AND teacher_id = %s
            """, (title, description, essay_type, due_date, guidelines, assignment_id, session['user_id']))
            conn.commit()
            conn.close()
            
            flash('Assignment updated successfully!', 'success')
            return redirect(url_for('view_assignment', assignment_id=assignment_id))
        
        # Get assignment details
        cursor.execute("""
            SELECT id, title, description, essay_type, due_date, guidelines
            FROM assignments
            WHERE id = %s AND teacher_id = %s
        """, (assignment_id, session['user_id']))
        assignment = cursor.fetchone()
        conn.close()
        
        if not assignment:
            flash('Assignment not found', 'error')
            return redirect(url_for('teacher_dashboard'))
        
        return render_template('teacher/edit_assignment.html', assignment=assignment)

    @app.route('/teacher/feedback/<int:essay_id>', methods=['GET', 'POST'])
    @login_required
    @role_required('teacher')
    def provide_feedback(essay_id):
        """Provide teacher feedback on essay"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if request.method == 'POST':
            feedback = request.form['feedback']
            
            # Get score overrides if provided
            ideas_score = request.form.get('ideas_score')
            organization_score = request.form.get('organization_score')
            style_score = request.form.get('style_score')
            grammar_score = request.form.get('grammar_score')
            
            # Convert empty strings to None for database
            ideas_score = float(ideas_score) if ideas_score else None
            organization_score = float(organization_score) if organization_score else None
            style_score = float(style_score) if style_score else None
            grammar_score = float(grammar_score) if grammar_score else None
            
            # Calculate total score if individual scores are provided
            total_score = None
            if all(score is not None for score in [ideas_score, organization_score, style_score, grammar_score]):
                total_score = ideas_score + organization_score + style_score + grammar_score
            
            # Update essay with feedback and scores
            update_query = """
                UPDATE essays SET 
                    teacher_feedback = %s, 
                    status = 'reviewed'
            """
            update_params = [feedback]
            
            if ideas_score is not None:
                update_query += ", ideas_score = %s"
                update_params.append(ideas_score)
            if organization_score is not None:
                update_query += ", organization_score = %s"
                update_params.append(organization_score)
            if style_score is not None:
                update_query += ", style_score = %s"
                update_params.append(style_score)
            if grammar_score is not None:
                update_query += ", grammar_score = %s"
                update_params.append(grammar_score)
            if total_score is not None:
                update_query += ", total_score = %s"
                update_params.append(total_score)
                
            update_query += " WHERE id = %s"
            update_params.append(essay_id)
            
            cursor.execute(update_query, update_params)
            conn.commit()
            flash('Feedback provided successfully!', 'success')
            return redirect(url_for('teacher_dashboard'))
        
        # Get essay details
        cursor.execute("""
            SELECT e.id, e.title, e.content, e.essay_type, e.feedback, e.teacher_feedback,
                   e.ideas_score, e.organization_score, e.style_score, e.grammar_score, 
                   e.total_score, u.username
            FROM essays e
            JOIN users u ON e.user_id = u.id
            WHERE e.id = %s AND u.role = 'student'
        """, (essay_id,))
        essay = cursor.fetchone()
        conn.close()
        
        if not essay:
            flash('Essay not found', 'error')
            return redirect(url_for('teacher_dashboard'))
        
        return render_template('teacher/feedback.html', essay=essay)

    @app.route('/teacher/profile', methods=['GET', 'POST'])
    @login_required
    @role_required('teacher')
    def teacher_profile():
        """Teacher profile page"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if request.method == 'POST':
            # Handle profile update
            username = request.form.get('username')
            email = request.form.get('email')
            
            # Update user profile
            cursor.execute("""
                UPDATE users SET username = %s, email = %s WHERE id = %s
            """, (username, email, session['user_id']))
            conn.commit()
            
            # Update session
            session['username'] = username
            
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('teacher_profile'))
        
        # Get current user info
        cursor.execute("""
            SELECT username, email, created_at
            FROM users WHERE id = %s
        """, (session['user_id'],))
        user_info = cursor.fetchone()
        
        conn.close()
        
        return render_template('teacher/profile.html', user_info=user_info)

    @app.route('/teacher/settings', methods=['GET', 'POST'])
    @login_required
    @role_required('teacher')
    def teacher_settings():
        """Teacher settings page"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if request.method == 'POST':
            # Handle settings update
            email = request.form.get('email')
            default_feedback_template = request.form.get('default_feedback_template', '')
            auto_grade_essays = request.form.get('auto_grade_essays') == 'on'
            
            # Update user settings
            cursor.execute("""
                UPDATE users SET 
                    email = %s, 
                    default_feedback_template = %s, 
                    auto_grade_essays = %s 
                WHERE id = %s
            """, (email, default_feedback_template, auto_grade_essays, session['user_id']))
            conn.commit()
            
            flash('Settings updated successfully!', 'success')
            return redirect(url_for('teacher_settings'))
        
        # Get current user settings
        cursor.execute("""
            SELECT email, default_feedback_template, auto_grade_essays
            FROM users WHERE id = %s
        """, (session['user_id'],))
        user_settings = cursor.fetchone()
        conn.close()
        
        if not user_settings:
            flash('User not found', 'error')
            return redirect(url_for('teacher_dashboard'))
        
        return render_template('teacher/settings.html', user_settings=user_settings)

    @app.route('/teacher/analytics')
    @login_required
    @role_required('teacher')
    def teacher_analytics():
        """Teacher analytics page"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get analytics data for assigned students
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT e.id) as total_essays,
                AVG(e.total_score) as avg_score,
                COUNT(DISTINCT sta.student_id) as total_students
            FROM student_teacher_assignments sta
            LEFT JOIN essays e ON sta.student_id = e.user_id
            WHERE sta.teacher_id = %s
        """, (session['user_id'],))
        overall_stats = cursor.fetchone()
        
        # Get score trends over time
        cursor.execute("""
            SELECT DATE(e.created_at) as date, AVG(e.total_score) as avg_score
            FROM essays e
            JOIN student_teacher_assignments sta ON e.user_id = sta.student_id
            WHERE sta.teacher_id = %s AND e.total_score IS NOT NULL
            GROUP BY DATE(e.created_at)
            ORDER BY date DESC
            LIMIT 30
        """, (session['user_id'],))
        score_trends = cursor.fetchall()
        
        # Get essay type distribution
        cursor.execute("""
            SELECT e.essay_type, COUNT(*) as count
            FROM essays e
            JOIN student_teacher_assignments sta ON e.user_id = sta.student_id
            WHERE sta.teacher_id = %s
            GROUP BY e.essay_type
        """, (session['user_id'],))
        essay_types = cursor.fetchall()
        
        conn.close()
        
        return render_template('teacher/analytics.html', 
                             overall_stats=overall_stats,
                             score_trends=score_trends,
                             essay_types=essay_types)

    # API Routes
    @app.route('/analyze', methods=['POST'])
    @login_required
    def analyze_essay():
        """Analyze essay with AI with enhanced progress tracking"""
        try:
            data = request.get_json()
            
            if not data:
                logger.error("No JSON data received")
                return jsonify({'error': 'No data provided'}), 400
            
            # Support both 'essay_text' and 'essay' field names for backward compatibility
            essay_text = data.get('essay_text', data.get('essay', '')).strip()
            essay_type = data.get('essay_type', 'auto').lower()
            coaching_level = data.get('coaching_level', 'medium').lower()
            suggestion_aggressiveness = data.get('suggestion_aggressiveness', 'medium').lower()
            assignment_id = data.get('assignment_id')  # Optional assignment ID
            
            if not essay_text:
                return jsonify({'error': 'Essay text is required'}), 400
            
            # Validate essay length
            if len(essay_text) < 50:
                return jsonify({'error': 'Essay too short (minimum 50 characters)'}), 400
            if len(essay_text) > 10000:
                return jsonify({'error': 'Essay too long (maximum 10000 characters)'}), 400
                
            # Validate essay type
            valid_types = ['auto', 'argumentative', 'narrative', 'literary', 'expository', 'descriptive', 'compare']
            if essay_type not in valid_types:
                return jsonify({'error': f'Invalid essay type. Must be one of: {", ".join(valid_types)}'}), 400
                
            # Validate coaching level
            valid_levels = ['light', 'medium', 'intensive']
            if coaching_level not in valid_levels:
                return jsonify({'error': f'Invalid coaching level. Must be one of: {", ".join(valid_levels)}'}), 400

            # Validate suggestion aggressiveness
            valid_aggressiveness = ['low', 'medium', 'high']
            if suggestion_aggressiveness not in valid_aggressiveness:
                return jsonify({'error': f'Invalid suggestion aggressiveness. Must be one of: {", ".join(valid_aggressiveness)}'}), 400
            
            logger.info(f"Processing essay: {len(essay_text)} chars, type: {essay_type}, level: {coaching_level}, aggressiveness: {suggestion_aggressiveness}")
            
            # Analyze essay with AI with comprehensive error handling
            try:
                analysis_result = analyze_essay_with_ai(
                    essay_text, 
                    essay_type, 
                    coaching_level, 
                    suggestion_aggressiveness
                )
                
                if not analysis_result:
                    logger.error("AI analysis returned no results")
                    return jsonify({
                        'error': 'Failed to analyze essay. Please try again later.',
                        'fallback': True
                    }), 500
                
                # Check if fallback was used
                if analysis_result.get('fallback_used'):
                    logger.warning("AI analysis used fallback due to service unavailability")
                    analysis_result['warning'] = 'AI service was temporarily unavailable. Results may be limited.'
                
                # Add processing time for user feedback
                analysis_result['processing_time'] = 'Analysis completed in real-time'
                
            except Exception as e:
                logger.error(f"AI analysis failed completely: {e}")
                return jsonify({
                    'error': 'Essay analysis service is temporarily unavailable. Please try again later.',
                    'details': 'Our AI analysis service is experiencing issues. Please check back in a few minutes.'
                }), 503
            
            # Save to database if user wants to save
            if data.get('save_to_db', False):
                try:
                    conn = get_db_connection()
                    if not conn:
                        logger.error("Database connection failed during essay save")
                        return jsonify({
                            'analysis': analysis_result,
                            'warning': 'Analysis completed but could not be saved to your profile due to database issues.'
                        })
                    
                    cursor = conn.cursor()
                    
                    # Save essay
                    cursor.execute("""
                        INSERT INTO essays (user_id, title, content, essay_type, feedback, 
                                          ideas_score, organization_score, style_score, grammar_score, 
                                          total_score, status, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        session['user_id'],
                        data.get('title', 'Untitled Essay'),
                        essay_text,
                        analysis_result.get('essay_type', 'Unknown'),
                        json.dumps(analysis_result),
                        analysis_result.get('scores', {}).get('ideas', 0),
                        analysis_result.get('scores', {}).get('organization', 0),
                        analysis_result.get('scores', {}).get('style', 0),
                        analysis_result.get('scores', {}).get('grammar', 0),
                        sum(analysis_result.get('scores', {}).values()),
                        'analyzed',
                        datetime.datetime.now()
                    ))
                    conn.commit()
                    conn.close()
                    logger.info("Essay saved to database successfully")
                    
                except Exception as e:
                    logger.error(f"Failed to save essay to database: {e}")
                    try:
                        if 'conn' in locals():
                            conn.close()
                    except:
                        pass
                    return jsonify({
                        'analysis': analysis_result,
                        'warning': 'Analysis completed but could not be saved to your profile.'
                    })
            
            # Save submission to database for students
            user = get_current_user()
            if user and user['role'] == 'student' and analysis_result.get('analysis_id'):
                success = save_submission_to_db(user['id'], analysis_result.get('analysis_id'), assignment_id)
                if success:
                    logger.info("Submission saved successfully")
                else:
                    logger.warning("Failed to save submission to database")
            
            return jsonify(analysis_result)
            
        except Exception as e:
            logger.error(f"Analysis error: {e}")
            return jsonify({'error': f'Analysis failed: {str(e)}'}), 500

    @app.route('/export', methods=['POST'])
    @login_required
    def export_to_word():
        """Export essay analysis to Word document"""
        data = request.get_json()
        
        if not data or 'essay' not in data or 'analysis' not in data:
            return jsonify({'error': 'Missing essay or analysis data'}), 400
        
        try:
            essay_text = data['essay']
            analysis_data = data['analysis']
            accepted_suggestions = data.get('acceptedSuggestions', [])
            
            # Ensure analysis_data is a dict, parse if string
            if isinstance(analysis_data, str):
                analysis_data = json.loads(analysis_data)

            # Normalize suggestions to list of dicts
            suggestions = analysis_data.get('suggestions', [])
            normalized_suggestions = []
            for s in suggestions:
                if isinstance(s, dict):
                    normalized_suggestions.append(s)
                elif isinstance(s, str):
                    normalized_suggestions.append({'type': 'General', 'text': s, 'reason': ''})
                else:
                    normalized_suggestions.append({'type': 'General', 'text': str(s), 'reason': ''})
            analysis_data['suggestions'] = normalized_suggestions

            doc = create_word_document_with_suggestions(essay_text, analysis_data, accepted_suggestions)
            
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.docx')
            doc.save(temp_file.name)
            temp_file.close()
            
            logger.info("Word document exported successfully")
            return send_file(
                temp_file.name,
                as_attachment=True,
                download_name='essay_analysis.docx',
                mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            )
        except Exception as e:
            logger.error(f"Export error: {e}")
            return jsonify({'error': f'Export failed: {str(e)}'}), 500

    # Error Handlers
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('500.html'), 500

    # Template Filters
    @app.template_filter('nl2br')
    def nl2br_filter(text):
        """Convert newlines to HTML breaks"""
        return text.replace('\n', '<br>') if text else ''
    
    # Performance Monitoring Routes
    @app.route('/admin/performance')
    @login_required
    @role_required('teacher')  # Only teachers can access performance stats
    def performance_dashboard():
        """Performance monitoring dashboard"""
        try:
            from performance_monitor import get_performance_stats
            stats = get_performance_stats()
            return jsonify(stats)
        except ImportError:
            return jsonify({'error': 'Performance monitoring not available'}), 503
        except Exception as e:
            logger.error(f"Error getting performance stats: {e}")
            return jsonify({'error': 'Failed to get performance statistics'}), 500
    
    @app.route('/admin/performance/cache/clear', methods=['POST'])
    @login_required
    @role_required('teacher')
    def clear_analysis_cache():
        """Clear the analysis cache"""
        try:
            from cache import clear_cache
            clear_cache()
            return jsonify({'message': 'Cache cleared successfully'})
        except ImportError:
            return jsonify({'error': 'Caching not available'}), 503
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return jsonify({'error': 'Failed to clear cache'}), 500
    
    @app.route('/admin/performance/reset', methods=['POST'])
    @login_required
    @role_required('teacher')
    def reset_performance_stats():
        """Reset performance statistics"""
        try:
            from performance_monitor import reset_performance_stats
            reset_performance_stats()
            return jsonify({'message': 'Performance statistics reset successfully'})
        except ImportError:
            return jsonify({'error': 'Performance monitoring not available'}), 503
        except Exception as e:
            logger.error(f"Error resetting performance stats: {e}")
            return jsonify({'error': 'Failed to reset performance statistics'}), 500
