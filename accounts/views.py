from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone
from django.db.models import Q
from .forms import CustomUserCreationForm, CustomAuthenticationForm
from .models import TeacherAssignmentRequest, StudentTeacherAssignment, CustomUser
from essays.utils import role_required


def index(request):
    """Home page view"""
    if request.user.is_authenticated:
        if request.user.is_student():
            return redirect('essays:dashboard')
        else:
            return redirect('analytics:teacher_dashboard')
    return render(request, 'accounts/index.html')


def signup(request):
    """User registration view"""
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, 'Account created successfully!')
            login(request, user)
            return redirect('accounts:index')
    else:
        form = CustomUserCreationForm()
    return render(request, 'accounts/signup.html', {'form': form})


def user_login(request):
    """User login view with robust feedback and redirect handling"""
    next_url = request.GET.get('next') or request.POST.get('next')
    if request.method == 'POST':
        print('DEBUG: Login POST received', request.POST)
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            print('DEBUG: Login form valid')
            user = form.get_user()
            if user is not None:
                print(f'DEBUG: Authenticating user {user.username} role={getattr(user, "role", None)}')
                login(request, user)
                # Prefer explicit next redirect if supplied and safe
                if next_url:
                    print(f'DEBUG: Redirecting to next={next_url}')
                    return redirect(next_url)
                if user.is_student():
                    print('DEBUG: Redirecting to student dashboard')
                    return redirect('essays:dashboard')
                print('DEBUG: Redirecting to teacher dashboard')
                return redirect('analytics:teacher_dashboard')
            # This branch rarely reached because valid form implies authenticated user
            messages.error(request, 'Authentication failed. Please try again.')
        else:
            print('DEBUG: Login form invalid', form.errors)
            # Surface form (non-field) errors
            for err in form.non_field_errors():
                messages.error(request, err)
    else:
        form = CustomAuthenticationForm(request)
    return render(request, 'login.html', {'form': form, 'next': next_url})


def user_logout(request):
    """User logout view"""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('accounts:index')


@login_required
def profile(request):
    """User profile view"""
    return render(request, 'accounts/profile.html')


@login_required
def settings(request):
    """User settings view"""
    if request.method == 'POST':
        user = request.user
        user.email = request.POST.get('email', user.email)
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.save()
        messages.success(request, 'Settings updated successfully!')
        return redirect('accounts:profile')
    
    return render(request, 'accounts/settings.html')


@login_required
@role_required('student')
def teacher_requests(request):
    """View for students to see teacher assignment requests"""
    print(f"DEBUG: User {request.user.username} accessing teacher requests page")
    print(f"DEBUG: User role: {request.user.role}")
    
    requests = TeacherAssignmentRequest.objects.filter(
        student=request.user,
        status='pending'
    ).select_related('teacher')
    
    print(f"DEBUG: Found {requests.count()} pending requests")
    
    return render(request, 'accounts/teacher_requests.html', {
        'requests': requests
    })


@login_required
@role_required('student')
def accept_teacher_request(request, request_id):
    """Accept a teacher assignment request"""
    teacher_request = get_object_or_404(
        TeacherAssignmentRequest,
        id=request_id,
        student=request.user,
        status='pending'
    )
    
    # Create student-teacher assignment
    assignment, created = StudentTeacherAssignment.objects.get_or_create(
        student=request.user,
        teacher=teacher_request.teacher
    )
    
    # Update request status
    teacher_request.status = 'accepted'
    teacher_request.responded_at = timezone.now()
    teacher_request.save()
    
    messages.success(request, f'You have accepted {teacher_request.teacher.get_full_name()}\'s assignment request!')
    return redirect('accounts:teacher_requests')


@login_required
@role_required('student')
def reject_teacher_request(request, request_id):
    """Reject a teacher assignment request"""
    teacher_request = get_object_or_404(
        TeacherAssignmentRequest,
        id=request_id,
        student=request.user,
        status='pending'
    )
    
    # Update request status
    teacher_request.status = 'rejected'
    teacher_request.responded_at = timezone.now()
    teacher_request.save()
    
    messages.success(request, f'You have rejected {teacher_request.teacher.get_full_name()}\'s assignment request.')
    return redirect('accounts:teacher_requests')


@login_required
@role_required('teacher')
def add_student(request):
    """View for teachers to add students via Gmail or username"""
    if request.method == 'POST':
        identifier = request.POST.get('identifier', '').strip()
        message = request.POST.get('message', '').strip()
        
        if not identifier:
            messages.error(request, 'Please provide a username or email address.')
            return render(request, 'accounts/teacher/add_student.html')
        
        # Try to find student by username or email
        try:
            if '@' in identifier:
                student = CustomUser.objects.get(email=identifier, role='student')
            else:
                student = CustomUser.objects.get(username=identifier, role='student')
        except CustomUser.DoesNotExist:
            messages.error(request, f'No student found with identifier: {identifier}')
            return render(request, 'accounts/teacher/add_student.html')
        
        # Check if already assigned
        if StudentTeacherAssignment.objects.filter(student=student, teacher=request.user).exists():
            messages.warning(request, f'{student.get_full_name() or student.username} is already your student.')
            return render(request, 'accounts/teacher/add_student.html')
        
        # Check if request already exists
        existing_request = TeacherAssignmentRequest.objects.filter(
            teacher=request.user,
            student=student
        ).first()
        
        if existing_request:
            if existing_request.status == 'pending':
                messages.warning(request, f'You already have a pending request to {student.get_full_name() or student.username}.')
            elif existing_request.status == 'rejected':
                messages.warning(request, f'{student.get_full_name() or student.username} has previously rejected your request.')
            else:
                messages.warning(request, f'You already have a processed request to {student.get_full_name() or student.username}.')
            return render(request, 'accounts/teacher/add_student.html')
        
        # Create new request
        TeacherAssignmentRequest.objects.create(
            teacher=request.user,
            student=student,
            message=message
        )
        
        messages.success(request, f'Assignment request sent to {student.get_full_name() or student.username}!')
        return redirect('accounts:my_students')
    
    return render(request, 'accounts/teacher/add_student.html')


@login_required
@role_required('teacher')
def my_students(request):
    """View for teachers to see their students and pending requests"""
    # Get assigned students
    assignments = StudentTeacherAssignment.objects.filter(
        teacher=request.user
    ).select_related('student').order_by('-assigned_at')
    
    # Get pending requests
    pending_requests = TeacherAssignmentRequest.objects.filter(
        teacher=request.user,
        status='pending'
    ).select_related('student').order_by('-created_at')
    
    # Get recent submissions from assigned students
    from essays.models import EssayAnalysis
    recent_submissions = EssayAnalysis.objects.filter(
        student__in=[assignment.student for assignment in assignments]
    ).select_related('student').order_by('-created_at')[:10]
    
    context = {
        'assignments': assignments,
        'pending_requests': pending_requests,
        'recent_submissions': recent_submissions,
    }
    
    return render(request, 'accounts/teacher/my_students.html', context)


@login_required
@role_required('teacher') 
def student_submissions(request, student_id):
    """View all submissions from a specific student"""
    student = get_object_or_404(CustomUser, id=student_id, role='student')
    
    # Check if student is assigned to this teacher
    if not StudentTeacherAssignment.objects.filter(student=student, teacher=request.user).exists():
        messages.error(request, 'This student is not assigned to you.')
        return redirect('accounts:my_students')
    
    from essays.models import EssayAnalysis, EssayFeedback
    from assignments.models import AssignmentSubmission
    
    # Get all essay analyses from this student
    essay_analyses = EssayAnalysis.objects.filter(
        student=student
    ).order_by('-created_at')
    
    # Get assignment submissions
    assignment_submissions = AssignmentSubmission.objects.filter(
        student=student,
        assignment__teacher=request.user
    ).select_related('assignment', 'essay_analysis').order_by('-submitted_at')
    
    # Add feedback info to analyses
    for analysis in essay_analyses:
        try:
            analysis.teacher_feedback = analysis.teacher_feedback
        except EssayFeedback.DoesNotExist:
            analysis.teacher_feedback = None
    
    context = {
        'student': student,
        'essay_analyses': essay_analyses,
        'assignment_submissions': assignment_submissions,
    }
    
    return render(request, 'accounts/teacher/student_submissions.html', context)


@login_required
@role_required('teacher')
def give_feedback(request, analysis_id):
    """Give feedback on a student's essay analysis"""
    from essays.models import EssayAnalysis, EssayFeedback
    
    analysis = get_object_or_404(EssayAnalysis, id=analysis_id)
    
    # Check if student is assigned to this teacher
    if not StudentTeacherAssignment.objects.filter(student=analysis.student, teacher=request.user).exists():
        messages.error(request, 'This student is not assigned to you.')
        return redirect('accounts:my_students')
    
    if request.method == 'POST':
        feedback_text = request.POST.get('feedback_text', '').strip()
        additional_score = request.POST.get('additional_score')
        
        if not feedback_text:
            messages.error(request, 'Please provide feedback text.')
            return render(request, 'accounts/teacher/give_feedback.html', {'analysis': analysis})
        
        # Convert additional_score to float if provided
        if additional_score:
            try:
                additional_score = float(additional_score)
                if additional_score < 0 or additional_score > 100:
                    messages.error(request, 'Score must be between 0 and 100.')
                    return render(request, 'accounts/teacher/give_feedback.html', {'analysis': analysis})
            except ValueError:
                messages.error(request, 'Invalid score format.')
                return render(request, 'accounts/teacher/give_feedback.html', {'analysis': analysis})
        else:
            additional_score = None
        
        # Create or update feedback
        feedback, created = EssayFeedback.objects.update_or_create(
            analysis=analysis,
            defaults={
                'teacher': request.user,
                'feedback_text': feedback_text,
                'additional_score': additional_score,
            }
        )
        
        action = 'added' if created else 'updated'
        messages.success(request, f'Feedback {action} successfully!')
        return redirect('accounts:student_submissions', student_id=analysis.student.id)
    
    # Check if feedback already exists
    try:
        existing_feedback = analysis.teacher_feedback
    except EssayFeedback.DoesNotExist:
        existing_feedback = None
    
    context = {
        'analysis': analysis,
        'existing_feedback': existing_feedback,
    }
    
    return render(request, 'accounts/teacher/give_feedback.html', context)
