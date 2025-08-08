from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Avg, Count, Q
from django.http import JsonResponse
from django.core.paginator import Paginator
import json
import logging

from essays.utils import role_required
from essays.models import EssayAnalysis, StudentSubmission
from assignments.models import Assignment, AssignmentSubmission
from accounts.models import CustomUser, StudentTeacherAssignment

logger = logging.getLogger(__name__)


@login_required
@role_required('teacher')
def teacher_dashboard(request):
    """Teacher dashboard with analytics"""
    try:
        # Get teacher's students
        student_assignments = StudentTeacherAssignment.objects.filter(
            teacher=request.user
        ).select_related('student')
        
        student_ids = [sa.student.id for sa in student_assignments]
        students = CustomUser.objects.filter(id__in=student_ids)
        
        # Get recent submissions from assigned students
        recent_submissions = StudentSubmission.objects.filter(
            student_id__in=student_ids
        ).select_related('analysis', 'student').order_by('-submitted_at')[:10]
        
        # Get teacher's assignments
        assignments = Assignment.objects.filter(
            teacher=request.user
        ).order_by('-created_at')[:5]
        
        # Statistics
        total_students = len(students)
        total_assignments = Assignment.objects.filter(teacher=request.user).count()
        total_submissions = StudentSubmission.objects.filter(student_id__in=student_ids).count()
        
        # Average scores
        avg_score = EssayAnalysis.objects.filter(
            student_id__in=student_ids
        ).aggregate(avg_score=Avg('overall_score'))['avg_score'] or 0
        
        context = {
            'recent_submissions': recent_submissions,
            'assignments': assignments,
            'total_students': total_students,
            'total_assignments': total_assignments,
            'total_submissions': total_submissions,
            'avg_score': round(avg_score, 1),
        }
        
        return render(request, 'analytics/teacher/dashboard.html', context)
        
    except Exception as e:
        logger.error(f"Error in teacher dashboard: {e}")
        messages.error(request, 'Error loading dashboard. Please try again.')
        return render(request, 'analytics/teacher/dashboard.html', {'error': True})


@login_required
@role_required('teacher')
def students_list(request):
    """List all assigned students"""
    try:
        # Get teacher's students
        student_assignments = StudentTeacherAssignment.objects.filter(
            teacher=request.user
        ).select_related('student')
        
        students_data = []
        for sa in student_assignments:
            student = sa.student
            
            # Get student statistics
            total_submissions = StudentSubmission.objects.filter(student=student).count()
            avg_score = EssayAnalysis.objects.filter(
                student=student
            ).aggregate(avg_score=Avg('overall_score'))['avg_score'] or 0
            
            # Get recent submission
            recent_submission = StudentSubmission.objects.filter(
                student=student
            ).select_related('analysis').order_by('-submitted_at').first()
            
            students_data.append({
                'student': student,
                'total_submissions': total_submissions,
                'avg_score': round(avg_score, 1),
                'recent_submission': recent_submission,
                'assigned_at': sa.assigned_at,
            })
        
        # Sort by average score (descending)
        students_data.sort(key=lambda x: x['avg_score'], reverse=True)
        
        context = {
            'students_data': students_data,
        }
        
        return render(request, 'analytics/teacher/students.html', context)
        
    except Exception as e:
        logger.error(f"Error loading students list: {e}")
        messages.error(request, 'Error loading students.')
        return render(request, 'analytics/teacher/students.html', {'error': True})


@login_required
@role_required('teacher')
def student_detail(request, student_id):
    """View detailed analytics for a specific student"""
    try:
        student = get_object_or_404(CustomUser, id=student_id, role='student')
        
        # Check if student is assigned to this teacher
        if not StudentTeacherAssignment.objects.filter(
            teacher=request.user,
            student=student
        ).exists():
            messages.error(request, 'This student is not assigned to you.')
            return redirect('analytics:students_list')
        
        # Get student's submissions
        submissions = StudentSubmission.objects.filter(
            student=student
        ).select_related('analysis').order_by('-submitted_at')
        
        # Pagination
        paginator = Paginator(submissions, 10)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        # Statistics
        total_submissions = submissions.count()
        if total_submissions > 0:
            avg_score = submissions.aggregate(
                avg_score=Avg('analysis__overall_score')
            )['avg_score'] or 0
            avg_grammar = submissions.aggregate(
                avg_grammar=Avg('analysis__grammar_score')
            )['avg_grammar'] or 0
            avg_clarity = submissions.aggregate(
                avg_clarity=Avg('analysis__clarity_score')
            )['avg_clarity'] or 0
            avg_structure = submissions.aggregate(
                avg_structure=Avg('analysis__structure_score')
            )['avg_structure'] or 0
            avg_content = submissions.aggregate(
                avg_content=Avg('analysis__content_score')
            )['avg_content'] or 0
        else:
            avg_score = avg_grammar = avg_clarity = avg_structure = avg_content = 0
        
        # Essay type distribution
        essay_types = EssayAnalysis.objects.filter(
            student=student
        ).values('essay_type').annotate(count=Count('id')).order_by('-count')
        
        context = {
            'student': student,
            'page_obj': page_obj,
            'total_submissions': total_submissions,
            'avg_score': round(avg_score, 1),
            'avg_grammar': round(avg_grammar, 1),
            'avg_clarity': round(avg_clarity, 1),
            'avg_structure': round(avg_structure, 1),
            'avg_content': round(avg_content, 1),
            'essay_types': essay_types,
        }
        
        return render(request, 'analytics/teacher/student_detail.html', context)
        
    except Exception as e:
        logger.error(f"Error loading student detail: {e}")
        messages.error(request, 'Error loading student details.')
        return redirect('analytics:students_list')


@login_required
@role_required('teacher')
def analytics_overview(request):
    """Analytics overview for teacher"""
    try:
        # Get teacher's students
        student_assignments = StudentTeacherAssignment.objects.filter(
            teacher=request.user
        ).select_related('student')
        
        student_ids = [sa.student.id for sa in student_assignments]
        
        # Overall statistics
        total_students = len(student_ids)
        total_submissions = StudentSubmission.objects.filter(student_id__in=student_ids).count()
        total_assignments = Assignment.objects.filter(teacher=request.user).count()
        
        # Score analytics
        score_stats = EssayAnalysis.objects.filter(
            student_id__in=student_ids
        ).aggregate(
            avg_overall=Avg('overall_score'),
            avg_grammar=Avg('grammar_score'),
            avg_clarity=Avg('clarity_score'),
            avg_structure=Avg('structure_score'),
            avg_content=Avg('content_score')
        )
        
        # Essay type distribution
        essay_type_dist = EssayAnalysis.objects.filter(
            student_id__in=student_ids
        ).values('essay_type').annotate(count=Count('id')).order_by('-count')
        
        # Performance trends (last 10 submissions)
        recent_analyses = EssayAnalysis.objects.filter(
            student_id__in=student_ids
        ).order_by('-created_at')[:10]
        
        trend_data = [
            {
                'date': analysis.created_at.strftime('%Y-%m-%d'),
                'score': analysis.overall_score,
                'student': analysis.student.username
            }
            for analysis in recent_analyses
        ]
        
        context = {
            'total_students': total_students,
            'total_submissions': total_submissions,
            'total_assignments': total_assignments,
            'score_stats': {
                'avg_overall': round(score_stats['avg_overall'] or 0, 1),
                'avg_grammar': round(score_stats['avg_grammar'] or 0, 1),
                'avg_clarity': round(score_stats['avg_clarity'] or 0, 1),
                'avg_structure': round(score_stats['avg_structure'] or 0, 1),
                'avg_content': round(score_stats['avg_content'] or 0, 1),
            },
            'essay_type_dist': essay_type_dist,
            'trend_data': json.dumps(trend_data),
        }
        
        return render(request, 'analytics/teacher/analytics.html', context)
        
    except Exception as e:
        logger.error(f"Error loading analytics overview: {e}")
        messages.error(request, 'Error loading analytics.')
        return render(request, 'analytics/teacher/analytics.html', {'error': True})


@login_required
@role_required('teacher')
def assignment_analytics(request, assignment_id):
    """Analytics for a specific assignment"""
    try:
        assignment = get_object_or_404(Assignment, id=assignment_id, teacher=request.user)
        
        # Get submissions for this assignment
        submissions = AssignmentSubmission.objects.filter(
            assignment=assignment
        ).select_related('student', 'essay_analysis')
        
        # Statistics
        total_submissions = submissions.count()
        graded_submissions = submissions.filter(status='graded').count()
        
        if total_submissions > 0:
            # AI scores
            ai_avg_score = submissions.aggregate(
                avg_score=Avg('essay_analysis__overall_score')
            )['avg_score'] or 0
            
            # Teacher scores
            teacher_scores = submissions.filter(teacher_score__isnull=False)
            teacher_avg_score = teacher_scores.aggregate(
                avg_score=Avg('teacher_score')
            )['avg_score'] or 0
            
            # Score distribution
            score_ranges = {
                '90-100': submissions.filter(essay_analysis__overall_score__gte=90).count(),
                '80-89': submissions.filter(
                    essay_analysis__overall_score__gte=80,
                    essay_analysis__overall_score__lt=90
                ).count(),
                '70-79': submissions.filter(
                    essay_analysis__overall_score__gte=70,
                    essay_analysis__overall_score__lt=80
                ).count(),
                '60-69': submissions.filter(
                    essay_analysis__overall_score__gte=60,
                    essay_analysis__overall_score__lt=70
                ).count(),
                'Below 60': submissions.filter(essay_analysis__overall_score__lt=60).count(),
            }
        else:
            ai_avg_score = teacher_avg_score = 0
            score_ranges = {}
        
        # Late submissions
        late_submissions = submissions.filter(
            submitted_at__gt=assignment.due_date
        ).count()
        
        context = {
            'assignment': assignment,
            'total_submissions': total_submissions,
            'graded_submissions': graded_submissions,
            'ai_avg_score': round(ai_avg_score, 1),
            'teacher_avg_score': round(teacher_avg_score, 1),
            'score_ranges': score_ranges,
            'late_submissions': late_submissions,
            'submissions': submissions,
        }
        
        return render(request, 'analytics/teacher/assignment_analytics.html', context)
        
    except Exception as e:
        logger.error(f"Error loading assignment analytics: {e}")
        messages.error(request, 'Error loading assignment analytics.')
        return redirect('assignments:assignments_list')


@login_required
@role_required('teacher')
def export_analytics_data(request):
    """Export analytics data as JSON"""
    try:
        # Get teacher's students
        student_assignments = StudentTeacherAssignment.objects.filter(
            teacher=request.user
        ).select_related('student')
        
        student_ids = [sa.student.id for sa in student_assignments]
        
        # Get all analyses for teacher's students
        analyses = EssayAnalysis.objects.filter(
            student_id__in=student_ids
        ).select_related('student').order_by('-created_at')
        
        # Prepare data for export
        export_data = []
        for analysis in analyses:
            export_data.append({
                'student_username': analysis.student.username,
                'essay_type': analysis.essay_type,
                'overall_score': analysis.overall_score,
                'grammar_score': analysis.grammar_score,
                'clarity_score': analysis.clarity_score,
                'structure_score': analysis.structure_score,
                'content_score': analysis.content_score,
                'created_at': analysis.created_at.isoformat(),
                'strengths': analysis.strengths,
                'areas_improvement': analysis.areas_improvement,
            })
        
        return JsonResponse({
            'success': True,
            'data': export_data,
            'total_records': len(export_data)
        })
        
    except Exception as e:
        logger.error(f"Error exporting analytics data: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Error exporting data'
        })
