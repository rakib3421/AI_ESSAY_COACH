from flask import Blueprint, render_template, request, redirect, url_for, session, flash, send_file, make_response
from utils import login_required, role_required, get_current_user, allowed_file, is_file_size_valid, extract_text_from_file, safe_get_string, create_word_document_with_suggestions, sanitize_text, validate_file_upload
from db import get_db_connection, save_analysis_to_db, save_submission_to_db, get_checklist_progress, update_checklist_progress, create_modular_rubric_engine
from ai import analyze_essay_with_ai, generate_step_wise_checklist
import os, datetime

student_bp = Blueprint('student', __name__, url_prefix='/student')

@student_bp.route('/dashboard')
@login_required
@role_required('student')
def student_dashboard():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT ea.id, 'Untitled Essay' as title, ea.essay_type, 'analyzed' as status,
               ea.created_at, ea.overall_score as total_score, NULL as teacher_feedback
        FROM student_submissions ss
        JOIN essay_analyses ea ON ss.analysis_id = ea.id
        WHERE ss.student_id = %s
        ORDER BY ea.created_at DESC
        LIMIT 5
    """, (session['user_id'],))
    recent_submissions = cursor.fetchall()
    # Additional queries and data preparation from routes.py
    conn.close()
    return render_template('student/dashboard.html', submissions=recent_submissions)

@student_bp.route('/upload', methods=['GET', 'POST'])
@login_required
@role_required('student')
def upload_essay():
    assignment_id = request.args.get('assignment_id', type=int)
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file selected', 'error')
            return redirect(request.url)
        file = request.files['file']
        # File upload and analysis logic
        return redirect(url_for('student.student_dashboard'))
    return render_template('student/upload.html')
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

@student_bp.route('/submit_assignment/<int:assignment_id>')
@login_required
@role_required('student')
def submit_assignment(assignment_id):
    # Assignment submission logic
    return redirect(url_for('student.view_assignments'))
    conn.close()
    return render_template('student/dashboard.html', submissions=recent_submissions)

@student_bp.route('/upload', methods=['GET', 'POST'])
@login_required
@role_required('student')
def upload_essay():
    assignment_id = request.args.get('assignment_id', type=int)
    # Extract assignment type if needed
    assignment_essay_type = None
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file selected', 'error')
            return redirect(request.url)
        file = request.files['file']
        # ...existing file upload and analysis logic...
        return redirect(url_for('student.student_dashboard'))
    return render_template('student/upload.html')

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
    # Profile management logic
    # ...existing profile code from routes.py...
    return render_template('student/profile.html')

@student_bp.route('/settings', methods=['GET', 'POST'])
@login_required
@role_required('student')
def student_settings():
    # Settings management logic
    # ...existing settings code from routes.py...
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

@student_bp.route('/submit_assignment/<int:assignment_id>')
@login_required
@role_required('student')
def submit_assignment(assignment_id):
    # Assign submission logic
    # ...existing submit assignment code...
    return redirect(url_for('student.student_assignments'))
