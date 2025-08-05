from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import datetime
from db import get_db_connection
from config import Config

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/')
def index():
    if 'user_id' in session:
        if session['role'] == 'student':
            return redirect(url_for('student.student_dashboard'))
        else:
            return redirect(url_for('teacher.teacher_dashboard'))
    return render_template('index.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
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
                return redirect(url_for('student.student_dashboard'))
            else:
                return redirect(url_for('teacher.teacher_dashboard'))
        else:
            flash('Invalid username or password', 'error')
    return render_template('login.html')

@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        role = request.form['role']
        if not username or not password or not email or not role:
            flash('All fields are required', 'error')
            return render_template('signup.html')
        if role not in ['student', 'teacher']:
            flash('Invalid role selected', 'error')
            return render_template('signup.html')
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
        if cursor.fetchone():
            flash('Username already exists', 'error')
            conn.close()
            return render_template('signup.html')
        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
            flash('Email already exists', 'error')
            conn.close()
            return render_template('signup.html')
        hashed_password = generate_password_hash(password)
        cursor.execute(
            "INSERT INTO users (username, password, email, role, created_at) VALUES (%s, %s, %s, %s, %s)",
            (username, hashed_password, email, role, datetime.datetime.now())
        )
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        session['user_id'] = user_id
        session['username'] = username
        session['role'] = role
        if role == 'student':
            return redirect(url_for('student.student_dashboard'))
        else:
            return redirect(url_for('teacher.teacher_dashboard'))
    return render_template('signup.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully', 'success')
    return redirect(url_for('auth.index'))
