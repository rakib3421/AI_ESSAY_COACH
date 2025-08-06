from flask import Blueprint, render_template, request, redirect, url_for, session, flash, send_file, make_response, jsonify
from utils import login_required, role_required, get_current_user, allowed_file, is_file_size_valid, extract_text_from_file, extract_text_from_filestorage, safe_get_string, create_word_document_with_suggestions, sanitize_text, validate_file_upload, store_analysis_temporarily, retrieve_analysis_temporarily, cleanup_expired_temp_data
from db import get_db_connection, save_analysis_to_db, save_submission_to_db, get_checklist_progress, update_checklist_progress, create_modular_rubric_engine
from ai import analyze_essay_with_ai, generate_step_wise_checklist
import os, datetime, pymysql, logging

# Set up logging
logger = logging.getLogger(__name__)

student_bp = Blueprint('student', __name__, url_prefix='/student')

@student_bp.route('/dashboard')
@login_required
@role_required('student')
def student_dashboard():
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    # Get recent submissions
    cursor.execute("""
        SELECT ea.id, 'Untitled Essay' as title, ea.essay_type, 'analyzed' as status,
               ea.created_at, ea.overall_score as score, NULL as teacher_feedback
        FROM student_submissions ss
        JOIN essay_analyses ea ON ss.analysis_id = ea.id
        WHERE ss.student_id = %s
        ORDER BY ea.created_at DESC
        LIMIT 5
    """, (session['user_id'],))
    recent_submissions = cursor.fetchall()
    
    # Get total essays count
    cursor.execute("""
        SELECT COUNT(*) as total_count FROM student_submissions WHERE student_id = %s
    """, (session['user_id'],))
    total_essays = cursor.fetchone()['total_count']
    
    # Get average score
    cursor.execute("""
        SELECT AVG(ea.overall_score) as avg_score
        FROM student_submissions ss
        JOIN essay_analyses ea ON ss.analysis_id = ea.id
        WHERE ss.student_id = %s AND ea.overall_score IS NOT NULL
    """, (session['user_id'],))
    avg_result = cursor.fetchone()
    average_score = round(avg_result['avg_score']) if avg_result['avg_score'] else 0
    
    # Get pending assignments count
    cursor.execute("""
        SELECT COUNT(*) as pending_count FROM assignments a
        LEFT JOIN student_submissions ss ON a.id = ss.assignment_id AND ss.student_id = %s
        WHERE ss.assignment_id IS NULL AND a.due_date >= CURRENT_DATE
    """, (session['user_id'],))
    pending_assignments = cursor.fetchone()['pending_count']
    
    # Get essays with feedback (mock data for now)
    essays_with_feedback = []
    
    # Get pending requests count (mock data for now) 
    pending_requests_count = 0
    
    # Get recent essays (same as submissions for now)
    recent_essays = recent_submissions
    
    # Get assignments for this student
    cursor.execute("""
        SELECT a.id, a.title, a.essay_type, a.due_date, a.created_at,
               CASE WHEN ss.id IS NOT NULL THEN 'Submitted' ELSE 'Pending' END as status
        FROM assignments a
        JOIN student_teacher_assignments sta ON a.teacher_id = sta.teacher_id
        LEFT JOIN student_submissions ss ON a.id = ss.assignment_id AND ss.student_id = %s
        WHERE sta.student_id = %s
        ORDER BY a.due_date ASC
        LIMIT 5
    """, (session['user_id'], session['user_id']))
    assignments = cursor.fetchall()
    
    # Get progress data (mock data - you can replace with actual progress calculations)
    progress = [75, 80, 85, 78]  # [ideas, organization, style, grammar] scores
    
    conn.close()
    
    return render_template('student/dashboard.html', 
                         submissions=recent_submissions,
                         total_essays=total_essays,
                         average_score=average_score,
                         pending_assignments=pending_assignments,
                         essays_with_feedback=essays_with_feedback,
                         pending_requests_count=pending_requests_count,
                         recent_essays=recent_submissions,
                         assignments=assignments,
                         progress=progress)

@student_bp.route('/upload', methods=['GET', 'POST'])
@login_required
@role_required('student')
def upload_essay():
    assignment_id = request.args.get('assignment_id', type=int)
    if request.method == 'POST':
        logger.info(f"POST request received. User ID: {session.get('user_id')}")
        logger.info(f"Form data: {dict(request.form)}")
        logger.info(f"Files in request: {list(request.files.keys())}")
        
        if 'file' not in request.files:
            logger.warning("No 'file' in request.files")
            flash('No file selected', 'error')
            return redirect(request.url)
        file = request.files['file']
        
        logger.info(f"File received: {file.filename}, size: {file.content_length}")
        
        if file.filename == '':
            logger.warning("Empty filename")
            flash('No file selected', 'error')
            return redirect(request.url)
        
        if not allowed_file(file.filename):
            logger.warning(f"Invalid file type: {file.filename}")
            flash('Invalid file type. Please upload a .txt, .docx, or .pdf file', 'error')
            return redirect(request.url)
        
        if not is_file_size_valid(file):
            flash('File size exceeds the maximum limit', 'error')
            return redirect(request.url)
        
        try:
            # Extract text from file
            essay_text = extract_text_from_filestorage(file)
            if not essay_text.strip():
                flash('The uploaded file appears to be empty or unreadable', 'error')
                return redirect(request.url)
            
            # Get parameters from form
            essay_type = request.form.get('essay_type', 'auto')
            coaching_level = request.form.get('coaching_level', 'medium')
            suggestion_aggressiveness = request.form.get('suggestion_aggressiveness', 'medium')
            title = request.form.get('title', 'Untitled Essay')
            
            # Get assignment ID from form or URL parameters
            assignment_id_form = request.form.get('assignment_id')
            if assignment_id_form:
                assignment_id = int(assignment_id_form)
            
            # Get assignment details if provided
            if assignment_id:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT essay_type FROM assignments WHERE id = %s", (assignment_id,))
                assignment = cursor.fetchone()
                if assignment:
                    essay_type = assignment['essay_type']
                conn.close()
            
            # Analyze essay with AI
            logger.info(f"Starting AI analysis for essay: {title}")
            analysis = analyze_essay_with_ai(essay_text, essay_type, coaching_level, suggestion_aggressiveness)
            logger.info("AI analysis completed successfully")
            
            # Save analysis to database
            logger.info("Saving analysis to database...")
            analysis_id = save_analysis_to_db(essay_text, analysis)
            logger.info(f"Analysis saved with ID: {analysis_id}")
            
            # Save submission
            logger.info("Saving submission to database...")
            final_assignment_id = assignment_id if assignment_id else None
            save_submission_to_db(session['user_id'], analysis_id, final_assignment_id)
            logger.info("Submission saved successfully")
            
            # Store analysis data temporarily instead of in session
            temp_data = {
                'essay_text': essay_text,
                'title': title,
                'analysis': analysis
            }
            temp_id = store_analysis_temporarily(temp_data)
            
            if temp_id:
                session['temp_analysis_id'] = temp_id
                logger.info(f"Analysis data stored temporarily with ID: {temp_id}")
            else:
                logger.error("Failed to store analysis data temporarily")
                flash('Analysis completed but display may be limited', 'warning')
            
            flash('Essay uploaded and analyzed successfully!', 'success')
            return redirect(url_for('student.analyze_view'))
            
        except Exception as e:
            logger.error(f'Error processing file: {str(e)}')
            flash(f'Error processing file: {str(e)}', 'error')
            return redirect(request.url)
    
    return render_template('student/upload.html')

@student_bp.route('/analyze', methods=['POST'])
@login_required
@role_required('student')
def analyze_essay():
    """
    Analyze essay text using AI with advanced options
    """
    try:
        data = request.get_json()
        
        if not data:
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
            return jsonify({'error': 'Essay too long (maximum 10,000 characters)'}), 400
        
        # Validate parameters
        valid_types = ['auto', 'argumentative', 'narrative', 'literary_analysis', 'hybrid', 'expository', 'descriptive', 'compare']
        valid_coaching = ['light', 'medium', 'intensive']
        valid_aggressiveness = ['low', 'medium', 'high']
        
        if essay_type not in valid_types:
            return jsonify({'error': f'Invalid essay type. Must be one of: {", ".join(valid_types)}'}), 400
        if coaching_level not in valid_coaching:
            return jsonify({'error': f'Invalid coaching level. Must be one of: {", ".join(valid_coaching)}'}), 400
        if suggestion_aggressiveness not in valid_aggressiveness:
            return jsonify({'error': f'Invalid suggestion aggressiveness. Must be one of: {", ".join(valid_aggressiveness)}'}), 400
        
        # Analyze essay with AI
        analysis_result = analyze_essay_with_ai(
            essay_text, 
            essay_type, 
            coaching_level, 
            suggestion_aggressiveness
        )
        
        # Save submission if requested
        if data.get('save_to_db', False):
            save_submission_to_db(session['user_id'], analysis_result.get('analysis_id'), assignment_id)
        
        return jsonify(analysis_result)
        
    except Exception as e:
        logger.error(f"Essay analysis error: {e}")
        return jsonify({'error': 'Failed to analyze essay. Please try again.'}), 500

@student_bp.route('/analyze-view')
@login_required
@role_required('student')
def analyze_view():
    """
    Display the essay analysis view with AI suggestions
    """
    # Check if we have temp analysis ID from upload
    temp_analysis_id = session.get('temp_analysis_id')
    if not temp_analysis_id:
        flash('No analysis data found. Please upload an essay first.', 'error')
        return redirect(url_for('student.upload_essay'))
    
    # Retrieve analysis data from temporary storage
    temp_analysis = retrieve_analysis_temporarily(temp_analysis_id)
    if not temp_analysis:
        flash('Analysis data has expired. Please upload your essay again.', 'error')
        return redirect(url_for('student.upload_essay'))
    
    # Clear the temp analysis ID from session
    session.pop('temp_analysis_id', None)
    
    return render_template('student/analyze_view.html', 
                         essay_text=temp_analysis['essay_text'],
                         title=temp_analysis['title'],
                         analysis=temp_analysis['analysis'])

@student_bp.route('/assignments/api')
@login_required
@role_required('student')
def assignments_api():
    """
    API endpoint to get assignments for the current student
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        cursor.execute("""
            SELECT a.id, a.title, a.essay_type, a.due_date
            FROM assignments a
            JOIN student_teacher_assignments sta ON a.teacher_id = sta.teacher_id
            WHERE sta.student_id = %s AND a.due_date >= CURRENT_DATE
            ORDER BY a.due_date ASC
        """, (session['user_id'],))
        
        assignments = cursor.fetchall()
        conn.close()
        
        return jsonify(assignments)
        
    except Exception as e:
        logger.error(f"Error loading assignments: {e}")
        return jsonify([])

@student_bp.route('/essays')
@login_required
@role_required('student')
def student_essays_list():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT ea.id, 'Untitled Essay' as title, ea.essay_type, ea.overall_score as total_score, 
               ea.created_at, 
               CASE 
                   WHEN e.teacher_feedback IS NOT NULL THEN 'reviewed'
                   ELSE 'analyzed'
               END as status, 
               e.teacher_feedback,
               ea.ideas_score, ea.organization_score, ea.style_score, ea.grammar_score
        FROM student_submissions ss
        JOIN essay_analyses ea ON ss.analysis_id = ea.id
        LEFT JOIN essays e ON e.user_id = ss.student_id 
            AND e.content = ea.essay_text 
            AND e.status = 'reviewed'
            AND e.teacher_feedback IS NOT NULL
        WHERE ss.student_id = %s 
        ORDER BY ea.created_at DESC
    """, (session['user_id'],))
    essays = cursor.fetchall()
    conn.close()
    return render_template('student/essays.html', essays=essays)

@student_bp.route('/view_essay/<int:essay_id>')
@login_required
@role_required('student')
def view_essay(essay_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT ea.id, 'Untitled Essay' as title, ea.essay_text as content, 
               ea.essay_type, ea.suggestions as feedback, ea.ideas_score, 
               ea.organization_score, ea.style_score, ea.grammar_score, 
               ea.overall_score as total_score, 'analyzed' as status
        FROM student_submissions ss
        JOIN essay_analyses ea ON ss.analysis_id = ea.id
        WHERE ea.id = %s AND ss.student_id = %s
    """, (essay_id, session['user_id']))
    essay = cursor.fetchone()
    conn.close()
    if not essay:
        flash('Essay not found', 'error')
        return redirect(url_for('student.student_dashboard'))
    return render_template('student/view_essay.html', essay=essay)

@student_bp.route('/assignments')
@login_required
@role_required('student')
def view_assignments():
    conn = get_db_connection()
    cursor = conn.cursor()
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
    conn.close()
    return render_template('student/assignments.html', assignments=assignments)

@student_bp.route('/progress')
@login_required
@role_required('student')
def student_progress():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT ea.id, 'Untitled Essay' as title, ea.essay_type, ea.ideas_score,
               ea.organization_score, ea.style_score, ea.grammar_score,
               ea.overall_score as total_score, ea.created_at, NULL as teacher_feedback
        FROM student_submissions ss
        JOIN essay_analyses ea ON ss.analysis_id = ea.id
        WHERE ss.student_id = %s AND ea.overall_score IS NOT NULL
        ORDER BY ea.created_at
    """, (session['user_id'],))
    essays = cursor.fetchall()
    cursor.execute("""
        SELECT DATE(ea.created_at) as date, AVG(ea.overall_score) as avg_score
        FROM student_submissions ss
        JOIN essay_analyses ea ON ss.analysis_id = ea.id
        WHERE ss.student_id = %s AND ea.overall_score IS NOT NULL
        GROUP BY DATE(ea.created_at)
        ORDER BY date
    """, (session['user_id'],))
    progress_data = cursor.fetchall()
    conn.close()
    return render_template('student/progress.html', essays=essays, progress=progress_data)

@student_bp.route('/profile', methods=['GET', 'POST'])
@login_required
@role_required('student')
def student_profile():
    if request.method == 'POST':
        # Handle profile updates
        conn = get_db_connection()
        cursor = conn.cursor()
        # Profile update logic here
        conn.close()
        flash('Profile updated successfully', 'success')
        return redirect(url_for('student.student_profile'))
    return render_template('student/profile.html')

@student_bp.route('/settings', methods=['GET', 'POST'])
@login_required
@role_required('student')
def student_settings():
    if request.method == 'POST':
        # Handle settings updates
        flash('Settings updated successfully', 'success')
        return redirect(url_for('student.student_settings'))
    return render_template('student/settings.html')

@student_bp.route('/feedback/<int:essay_id>')
@login_required
@role_required('student')
def student_feedback(essay_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT ea.overall_score, e.teacher_feedback
        FROM essay_analyses ea
        JOIN essays e ON ea.id = e.analysis_id
        WHERE ea.id = %s
    """, (essay_id,))
    feedback = cursor.fetchone()
    conn.close()
    return render_template('student/feedback.html', feedback=feedback)

@student_bp.route('/requests')
@login_required
@role_required('student')
def student_requests():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, assignment_id, status FROM assignment_requests WHERE student_id = %s", (session['user_id'],))
    requests = cursor.fetchall()
    conn.close()
    return render_template('student/requests.html', requests=requests)

@student_bp.route('/accept_assignment_request/<int:request_id>', methods=['POST'])
@login_required
@role_required('student')
def accept_assignment_request(request_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE assignment_requests SET status = 'accepted' WHERE id = %s AND student_id = %s", 
                   (request_id, session['user_id']))
    conn.commit()
    conn.close()
    flash('Assignment request accepted successfully', 'success')
    return redirect(url_for('student.student_requests'))

@student_bp.route('/reject_assignment_request/<int:request_id>', methods=['POST'])
@login_required
@role_required('student')
def reject_assignment_request(request_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE assignment_requests SET status = 'rejected' WHERE id = %s AND student_id = %s", 
                   (request_id, session['user_id']))
    conn.commit()
    conn.close()
    flash('Assignment request rejected', 'info')
    return redirect(url_for('student.student_requests'))

@student_bp.route('/submit_assignment/<int:assignment_id>')
@login_required
@role_required('student')
def submit_assignment(assignment_id):
    # Assignment submission logic
    return redirect(url_for('student.view_assignments'))

@student_bp.route('/cleanup-temp', methods=['POST'])
@login_required
@role_required('student')  # Could be changed to admin role if needed
def cleanup_temp():
    """Manual cleanup of expired temporary files"""
    try:
        cleanup_expired_temp_data()
        flash('Temporary files cleaned up successfully', 'success')
    except Exception as e:
        logger.error(f"Error during manual cleanup: {e}")
        flash('Error during cleanup', 'error')
    
    return redirect(request.referrer or url_for('student.student_dashboard'))
