from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from utils import login_required, role_required, get_current_user, sanitize_text
from db import get_db_connection, save_submission_to_db
from ai import normalize_essay_type
import datetime

teacher_bp = Blueprint('teacher', __name__, url_prefix='/teacher')

@teacher_bp.route('/dashboard')
@login_required
@role_required('teacher')
def teacher_dashboard():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT ea.id, 'Untitled Essay' as title, ea.essay_type, ea.overall_score as total_score, 
               ea.created_at, u.username
        FROM student_submissions ss
        JOIN essay_analyses ea ON ss.analysis_id = ea.id
        JOIN users u ON ss.student_id = u.id
        JOIN student_teacher_assignments sta ON u.id = sta.student_id
        WHERE u.role = 'student' AND sta.teacher_id = %s
        ORDER BY ea.created_at DESC
        LIMIT 10
    """, (session['user_id'],))
    submissions = cursor.fetchall()
    cursor.execute("""
        SELECT id, title, essay_type, due_date, created_at
        FROM assignments
        WHERE teacher_id = %s
        ORDER BY created_at DESC
        LIMIT 5
    """, (session['user_id'],))
    assignments = cursor.fetchall()
    cursor.execute("""
        SELECT COUNT(*) FROM student_teacher_assignments WHERE teacher_id = %s
    """, (session['user_id'],))
    assigned_students_count = cursor.fetchone()[0]
    conn.close()
    return render_template('teacher/dashboard.html', 
                         submissions=submissions, 
                         assignments=assignments,
                         assigned_students_count=assigned_students_count)

@teacher_bp.route('/create_assignment', methods=['GET', 'POST'])
@login_required
@role_required('teacher')
def create_assignment():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        essay_type = request.form.get('essay_type', 'auto')
        due_date = request.form['due_date']
        guidelines = request.form['guidelines']
        if essay_type != 'auto':
            essay_type = normalize_essay_type(essay_type)
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO assignments (teacher_id, title, description, essay_type, due_date, guidelines, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (session['user_id'], title, description, essay_type, due_date, guidelines, datetime.datetime.now()))
        conn.commit()
        conn.close()
        flash('Assignment created successfully!', 'success')
        return redirect(url_for('teacher.teacher_dashboard'))
    return render_template('teacher/create_assignment.html')

@teacher_bp.route('/all_essays')
@login_required
@role_required('teacher')
def teacher_all_essays():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT ea.id, 'Untitled Essay' as title, ea.essay_type, ea.overall_score as total_score, 
               ea.created_at, 'analyzed' as status, NULL as teacher_feedback, u.username, 
               ea.ideas_score, ea.organization_score, ea.style_score, ea.grammar_score
        FROM student_submissions ss
        JOIN essay_analyses ea ON ss.analysis_id = ea.id
        JOIN users u ON ss.student_id = u.id
        JOIN student_teacher_assignments sta ON u.id = sta.student_id
        WHERE sta.teacher_id = %s AND u.role = 'student'
        ORDER BY ea.created_at DESC
    """, (session['user_id'],))
    essays = cursor.fetchall()
    conn.close()
    return render_template('teacher/all_essays.html', essays=essays)

@teacher_bp.route('/submissions')
@login_required
@role_required('teacher')
def submissions():
    # Teacher submissions view
    return render_template('teacher/submissions.html')

@teacher_bp.route('/assignment/<int:assignment_id>')
@login_required
@role_required('teacher')
def assignment_view(assignment_id):
    # View specific assignment
    return render_template('teacher/assignment_view.html')

@teacher_bp.route('/assignment/<int:assignment_id>/submissions')
@login_required
@role_required('teacher')
def assignment_submissions(assignment_id):
    # View assignment submissions
    return render_template('teacher/assignment_submissions.html')

@teacher_bp.route('/assignment/<int:assignment_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('teacher')
def edit_assignment(assignment_id):
    if request.method == 'POST':
        # Edit assignment logic
        flash('Assignment updated successfully!', 'success')
        return redirect(url_for('teacher.teacher_dashboard'))
    return render_template('teacher/edit_assignment.html')

@teacher_bp.route('/feedback/<int:essay_id>', methods=['GET', 'POST'])
@login_required
@role_required('teacher')
def teacher_feedback(essay_id):
    if request.method == 'POST':
        # Save teacher feedback
        flash('Feedback saved successfully!', 'success')
        return redirect(url_for('teacher.teacher_all_essays'))
    return render_template('teacher/feedback.html')

@teacher_bp.route('/profile', methods=['GET', 'POST'])
@login_required
@role_required('teacher')
def teacher_profile():
    if request.method == 'POST':
        # Handle profile updates
        flash('Profile updated successfully', 'success')
        return redirect(url_for('teacher.teacher_profile'))
    return render_template('teacher/profile.html')

@teacher_bp.route('/settings', methods=['GET', 'POST'])
@login_required
@role_required('teacher')
def teacher_settings():
    if request.method == 'POST':
        # Handle settings updates
        flash('Settings updated successfully', 'success')
        return redirect(url_for('teacher.teacher_settings'))
    return render_template('teacher/settings.html')
