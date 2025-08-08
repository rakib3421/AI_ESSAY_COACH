from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
import logging

from .models import Assignment, AssignmentSubmission
from .forms import AssignmentForm, AssignmentSubmissionForm, GradingForm
from essays.utils import role_required, validate_file_upload, extract_text_from_file, sanitize_text
from essays.ai_service import analyze_essay_with_ai, save_analysis_to_database
from essays.models import EssayAnalysis, StudentSubmission
from accounts.models import StudentTeacherAssignment

logger = logging.getLogger(__name__)


@login_required
@role_required('teacher')
def create_assignment(request):
    """Create a new assignment"""
    if request.method == 'POST':
        form = AssignmentForm(request.POST)
        if form.is_valid():
            try:
                assignment = form.save(commit=False)
                assignment.teacher = request.user
                assignment.save()
                
                messages.success(request, 'Assignment created successfully!')
                return redirect('assignments:assignment_detail', assignment_id=assignment.id)
                
            except Exception as e:
                logger.error(f"Error creating assignment: {e}")
                messages.error(request, 'Error creating assignment. Please try again.')
    else:
        form = AssignmentForm()
    
    return render(request, 'assignments/teacher/create_assignment.html', {'form': form})


@login_required
@role_required('teacher')
def edit_assignment(request, assignment_id):
    """Edit an existing assignment"""
    assignment = get_object_or_404(Assignment, id=assignment_id, teacher=request.user)
    
    if request.method == 'POST':
        form = AssignmentForm(request.POST, instance=assignment)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, 'Assignment updated successfully!')
                return redirect('assignments:assignment_detail', assignment_id=assignment.id)
                
            except Exception as e:
                logger.error(f"Error updating assignment: {e}")
                messages.error(request, 'Error updating assignment. Please try again.')
    else:
        form = AssignmentForm(instance=assignment)
    
    return render(request, 'assignments/teacher/edit_assignment.html', {
        'form': form,
        'assignment': assignment
    })


@login_required
def assignment_detail(request, assignment_id):
    """View assignment details"""
    assignment = get_object_or_404(Assignment, id=assignment_id)
    
    # Check permissions
    if request.user.role == 'teacher' and assignment.teacher != request.user:
        messages.error(request, 'You do not have permission to view this assignment.')
        return redirect('analytics:teacher_dashboard')
    
    if request.user.role == 'student':
        # Check if student is assigned to this teacher
        if not StudentTeacherAssignment.objects.filter(
            student=request.user,
            teacher=assignment.teacher
        ).exists():
            messages.error(request, 'You are not assigned to this teacher.')
            return redirect('essays:dashboard')
    
    # Get submission if exists
    submission = None
    if request.user.role == 'student':
        submission = AssignmentSubmission.objects.filter(
            assignment=assignment,
            student=request.user
        ).first()
    
    context = {
        'assignment': assignment,
        'submission': submission,
        'is_overdue': assignment.is_overdue(),
    }
    
    return render(request, 'assignments/assignment_detail.html', context)


@login_required
@role_required('student')
def submit_assignment(request, assignment_id):
    """Submit an assignment"""
    assignment = get_object_or_404(Assignment, id=assignment_id)
    
    # Check if already submitted
    existing_submission = AssignmentSubmission.objects.filter(
        assignment=assignment,
        student=request.user
    ).first()
    
    if existing_submission:
        messages.warning(request, 'You have already submitted this assignment.')
        return redirect('assignments:assignment_detail', assignment_id=assignment.id)
    
    # Check if student is assigned to this teacher
    if not StudentTeacherAssignment.objects.filter(
        student=request.user,
        teacher=assignment.teacher
    ).exists():
        messages.error(request, 'You are not assigned to this teacher.')
        return redirect('essays:dashboard')
    
    if request.method == 'POST':
        form = AssignmentSubmissionForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                submission_method = form.cleaned_data['submission_method']
                
                if submission_method == 'upload':
                    uploaded_file = request.FILES['essay_file']
                    
                    # Validate file
                    is_valid, error_message = validate_file_upload(uploaded_file)
                    if not is_valid:
                        messages.error(request, error_message)
                        return render(request, 'assignments/student/submit_assignment.html', {
                            'form': form,
                            'assignment': assignment
                        })
                    
                    # Extract text
                    essay_text = extract_text_from_file(uploaded_file)
                    file_name = uploaded_file.name
                    
                else:  # paste method
                    essay_text = sanitize_text(form.cleaned_data['essay_text'])
                    file_name = 'Pasted Text'
                
                # Analyze with AI
                analysis_result = analyze_essay_with_ai(essay_text, assignment.essay_type)
                
                # Save analysis
                analysis = save_analysis_to_database(request.user, essay_text, assignment.essay_type, analysis_result)
                
                # Create assignment submission
                submission = AssignmentSubmission.objects.create(
                    assignment=assignment,
                    student=request.user,
                    essay_analysis=analysis,
                    submission_text=essay_text,
                    file_name=file_name
                )
                
                # Create regular submission record
                StudentSubmission.objects.create(
                    student=request.user,
                    analysis=analysis,
                    file_name=file_name
                )
                
                messages.success(request, 'Assignment submitted successfully!')
                return redirect('assignments:assignment_detail', assignment_id=assignment.id)
                
            except Exception as e:
                logger.error(f"Error submitting assignment: {e}")
                messages.error(request, 'Error submitting assignment. Please try again.')
    else:
        form = AssignmentSubmissionForm()
    
    return render(request, 'assignments/student/submit_assignment.html', {
        'form': form,
        'assignment': assignment
    })


@login_required
@role_required('teacher')
def assignment_submissions(request, assignment_id):
    """View all submissions for an assignment"""
    assignment = get_object_or_404(Assignment, id=assignment_id, teacher=request.user)
    
    submissions = AssignmentSubmission.objects.filter(
        assignment=assignment
    ).select_related('student', 'essay_analysis').order_by('-submitted_at')
    
    # Pagination
    paginator = Paginator(submissions, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'assignment': assignment,
        'page_obj': page_obj,
    }
    
    return render(request, 'assignments/teacher/assignment_submissions.html', context)


@login_required
@role_required('teacher')
def grade_submission(request, submission_id):
    """Grade a student submission"""
    submission = get_object_or_404(
        AssignmentSubmission,
        id=submission_id,
        assignment__teacher=request.user
    )
    
    if request.method == 'POST':
        form = GradingForm(request.POST, instance=submission, assignment=submission.assignment)
        if form.is_valid():
            try:
                graded_submission = form.save(commit=False)
                graded_submission.status = 'graded'
                graded_submission.graded_at = timezone.now()
                graded_submission.save()
                
                messages.success(request, 'Submission graded successfully!')
                return redirect('assignments:assignment_submissions', assignment_id=submission.assignment.id)
                
            except Exception as e:
                logger.error(f"Error grading submission: {e}")
                messages.error(request, 'Error grading submission. Please try again.')
    else:
        form = GradingForm(instance=submission, assignment=submission.assignment)
    
    context = {
        'submission': submission,
        'form': form,
    }
    
    return render(request, 'assignments/teacher/grade_submission.html', context)


@login_required
@role_required('teacher')
def assignments_list(request):
    """List all teacher's assignments"""
    assignments = Assignment.objects.filter(
        teacher=request.user
    ).order_by('-created_at')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        assignments = assignments.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(assignments, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
    }
    
    return render(request, 'assignments/teacher/assignments_list.html', context)


@login_required
@role_required('student')
def student_assignments(request):
    """List assignments for student"""
    # Get all teachers assigned to this student
    teacher_assignments = StudentTeacherAssignment.objects.filter(
        student=request.user
    ).select_related('teacher')
    
    teacher_ids = [ta.teacher.id for ta in teacher_assignments]
    
    # Get assignments from assigned teachers
    assignments = Assignment.objects.filter(
        teacher_id__in=teacher_ids,
        is_active=True
    ).order_by('-created_at')
    
    # Get student's submissions
    submissions = AssignmentSubmission.objects.filter(
        student=request.user
    ).select_related('assignment')
    
    submitted_assignment_ids = {sub.assignment.id for sub in submissions}
    
    # Add submission status to assignments
    for assignment in assignments:
        assignment.is_submitted = assignment.id in submitted_assignment_ids
        assignment.submission = next(
            (sub for sub in submissions if sub.assignment.id == assignment.id),
            None
        )
    
    context = {
        'assignments': assignments,
    }
    
    return render(request, 'assignments/student/assignments_list.html', context)
