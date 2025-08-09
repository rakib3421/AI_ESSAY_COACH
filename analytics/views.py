from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Avg, Count, Q
from django.http import JsonResponse
from django.core.paginator import Paginator
import json
import logging

from essays.utils import role_required, classify_score, display_essay_type, rubric_percent, build_score_distribution, build_type_distribution
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
        
        # Recent submissions with presentation fields
        recent_submissions_qs = StudentSubmission.objects.filter(
            student_id__in=student_ids
        ).select_related('analysis', 'student').order_by('-submitted_at')[:10]
        recent_submissions = []
        for sub in recent_submissions_qs:
            analysis = sub.analysis
            score_class, score_display = classify_score(analysis.overall_score if analysis else None)
            recent_submissions.append({
                'id': sub.id,
                'student_name': sub.student.get_full_name() or sub.student.username,
                'title': (analysis.detailed_feedback.get('title') if analysis and isinstance(analysis.detailed_feedback, dict) else '') or 'Untitled',
                'essay_type_display': display_essay_type(analysis.essay_type if analysis else None),
                'created_at': sub.submitted_at,
                'score': None if score_display == 'Pending' else score_display.rstrip('%'),
                'score_class': score_class,
            })
        
        # Get teacher's assignments
        assignments_qs = Assignment.objects.filter(
            teacher=request.user
        ).order_by('-created_at')[:5]
        assignments = []
        for a in assignments_qs:
            assignments.append((a.id, a.title, a.essay_type, a.due_date, display_essay_type(a.essay_type)))
        
        # Statistics
        total_students = len(students)
        total_assignments = Assignment.objects.filter(teacher=request.user).count()
        total_submissions = StudentSubmission.objects.filter(student_id__in=student_ids).count()
        
        # Average scores
        avg_score = EssayAnalysis.objects.filter(
            student_id__in=student_ids
        ).aggregate(avg_score=Avg('overall_score'))['avg_score'] or 0
        
        # Chart data (score distribution + type distribution + rubric averages)
        analyses_qs = EssayAnalysis.objects.filter(student_id__in=student_ids)
        # Score buckets
        buckets = [
            ('0-59', analyses_qs.filter(overall_score__lt=60).count()),
            ('60-69', analyses_qs.filter(overall_score__gte=60, overall_score__lt=70).count()),
            ('70-79', analyses_qs.filter(overall_score__gte=70, overall_score__lt=80).count()),
            ('80-89', analyses_qs.filter(overall_score__gte=80, overall_score__lt=90).count()),
            ('90-100', analyses_qs.filter(overall_score__gte=90).count()),
        ]
        score_chart = build_score_distribution(buckets)
        
        # Type counts
        type_counts_raw = analyses_qs.values('essay_type').annotate(count=Count('id'))
        type_counts = {row['essay_type']: row['count'] for row in type_counts_raw}
        type_chart = build_type_distribution(type_counts)
        
        # Rubric averages for dashboard
        rubric_averages = analyses_qs.aggregate(
            avg_grammar=Avg('grammar_score'),
            avg_clarity=Avg('clarity_score'),
            avg_structure=Avg('structure_score'),
            avg_content=Avg('content_score')
        )

        context = {
            'recent_submissions': recent_submissions,
            'assignments': assignments,
            'total_students': total_students,
            'total_assignments': total_assignments,
            'total_submissions': total_submissions,
            'avg_score': round(avg_score, 1),
            'score_chart_json': json.dumps(score_chart),
            'type_chart_json': json.dumps(type_chart),
            'rubric_averages': {
                'grammar': round(rubric_averages['avg_grammar'] or 0, 1),
                'clarity': round(rubric_averages['avg_clarity'] or 0, 1),
                'structure': round(rubric_averages['avg_structure'] or 0, 1),
                'content': round(rubric_averages['avg_content'] or 0, 1),
            },
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
            
            score_class, score_display = classify_score(avg_score)
            students_data.append({
                'student': student,
                'total_submissions': total_submissions,
                'avg_score': round(avg_score, 1),
                'avg_score_class': score_class,
                'recent_submission': recent_submission,
                'assigned_at': sa.assigned_at,
            })
        
        # Sort by average score (descending)
        students_data.sort(key=lambda x: x['avg_score'], reverse=True)

        context = {'students_data': students_data}
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
        
        # Score progression data for rubric components
        score_history = []
        for submission in submissions.order_by('submitted_at')[:20]:  # Last 20 submissions for progression
            if submission.analysis:
                score_history.append({
                    'date': submission.submitted_at.strftime('%Y-%m-%d'),
                    'overall_score': submission.analysis.overall_score,
                    'grammar_score': submission.analysis.grammar_score,
                    'clarity_score': submission.analysis.clarity_score,
                    'structure_score': submission.analysis.structure_score,
                    'content_score': submission.analysis.content_score,
                })
        
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
            'score_history': score_history,
            'essay_types': essay_types,
        }
        
        return render(request, 'analytics/teacher/student_detail.html', context)
        
    except Exception as e:
        logger.error(f"Error loading student detail: {e}")
        messages.error(request, 'Error loading student details.')
        return redirect('analytics:students_list')


@login_required
@role_required('teacher')
def student_rubric_progression(request, student_id):
    """View detailed rubric score progression for a specific student"""
    try:
        student = get_object_or_404(CustomUser, id=student_id, role='student')
        
        # Check if student is assigned to this teacher
        if not StudentTeacherAssignment.objects.filter(
            teacher=request.user,
            student=student
        ).exists():
            messages.error(request, 'This student is not assigned to you.')
            return redirect('analytics:students_list')
        
        # Get all student's analyses ordered by date
        analyses = EssayAnalysis.objects.filter(
            student=student
        ).order_by('created_at')
        
        # Prepare rubric progression data
        rubric_progression = {
            'dates': [],
            'grammar_scores': [],
            'clarity_scores': [],
            'structure_scores': [],
            'content_scores': [],
            'overall_scores': []
        }
        
        for analysis in analyses:
            rubric_progression['dates'].append(analysis.created_at.strftime('%Y-%m-%d'))
            rubric_progression['grammar_scores'].append(analysis.grammar_score)
            rubric_progression['clarity_scores'].append(analysis.clarity_score)
            rubric_progression['structure_scores'].append(analysis.structure_score)
            rubric_progression['content_scores'].append(analysis.content_score)
            rubric_progression['overall_scores'].append(analysis.overall_score)
        
        # Calculate improvement metrics
        improvement_metrics = {}
        for rubric_type in ['grammar', 'clarity', 'structure', 'content']:
            scores = rubric_progression[f'{rubric_type}_scores']
            if len(scores) >= 2:
                improvement = scores[-1] - scores[0]  # Latest - First
                improvement_metrics[rubric_type] = {
                    'improvement': round(improvement, 1),
                    'trend': 'up' if improvement > 0 else 'down' if improvement < 0 else 'stable'
                }
            else:
                improvement_metrics[rubric_type] = {
                    'improvement': 0,
                    'trend': 'stable'
                }
        
        # Get latest scores for comparison
        latest_analysis = analyses.last() if analyses else None
        
        context = {
            'student': student,
            'rubric_progression': json.dumps(rubric_progression),
            'improvement_metrics': improvement_metrics,
            'latest_analysis': latest_analysis,
            'total_essays': analyses.count(),
        }
        
        return render(request, 'analytics/teacher/student_rubric_progression.html', context)
        
    except Exception as e:
        logger.error(f"Error loading student rubric progression: {e}")
        messages.error(request, 'Error loading rubric progression.')
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
        
        # Performance trends (last 10 submissions with rubric breakdown)
        recent_analyses = EssayAnalysis.objects.filter(
            student_id__in=student_ids
        ).order_by('-created_at')[:10]
        
        trend_data = []
        rubric_trend_data = {
            'grammar': [],
            'clarity': [],
            'structure': [],
            'content': []
        }
        
        for analysis in recent_analyses:
            # Overall trend data
            trend_data.append({
                'date': analysis.created_at.strftime('%Y-%m-%d'),
                'score': analysis.overall_score,
                'student': analysis.student.username
            })
            
            # Rubric component trend data
            rubric_trend_data['grammar'].append({
                'date': analysis.created_at.strftime('%Y-%m-%d'),
                'score': analysis.grammar_score
            })
            rubric_trend_data['clarity'].append({
                'date': analysis.created_at.strftime('%Y-%m-%d'),
                'score': analysis.clarity_score
            })
            rubric_trend_data['structure'].append({
                'date': analysis.created_at.strftime('%Y-%m-%d'),
                'score': analysis.structure_score
            })
            rubric_trend_data['content'].append({
                'date': analysis.created_at.strftime('%Y-%m-%d'),
                'score': analysis.content_score
            })
        
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
            'rubric_trend_data': json.dumps(rubric_trend_data),
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
                'student_name': analysis.student.get_full_name(),
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
