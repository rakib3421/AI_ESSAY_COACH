from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.db.models import Avg, Count, Q
from django.utils import timezone
import json
import logging
import uuid

from .models import EssayAnalysis, StudentSubmission, ChecklistProgress, EssayFeedback
from .forms import EssayUploadForm, EssayTextForm, FeedbackForm
from .utils import role_required, validate_file_upload, extract_text_from_file, sanitize_text, create_word_document_with_suggestions, store_analysis_temporarily, retrieve_analysis_temporarily
from .ai_service import analyze_essay_with_ai, generate_step_wise_checklist, save_analysis_to_database, save_checklist_progress

logger = logging.getLogger(__name__)


@login_required
@role_required('student')
def dashboard(request):
    """Student dashboard view"""
    try:
        # Get recent submissions
        recent_submissions = StudentSubmission.objects.filter(
            student=request.user
        ).select_related('analysis').order_by('-submitted_at')[:5]
        
        # Get essays with feedback (separate query to avoid slice issue)
        essays_with_feedback = StudentSubmission.objects.filter(
            student=request.user,
            analysis__teacher_feedback__isnull=False
        )
        
        # Get progress statistics
        total_essays = StudentSubmission.objects.filter(student=request.user).count()
        avg_score = EssayAnalysis.objects.filter(
            student=request.user
        ).aggregate(avg_score=Avg('overall_score'))['avg_score'] or 0
        
        # Get improvement progress
        progress_data = ChecklistProgress.objects.filter(
            student=request.user
        ).order_by('-last_updated')[:3]
        
        # Calculate writing dimension progress (Ideas, Organization, Style, Grammar)
        analyses = EssayAnalysis.objects.filter(student=request.user)
        progress = [0, 0, 0, 0]  # Default values
        
        if analyses.exists():
            # Get the latest scores for each dimension
            latest_analysis = analyses.order_by('-created_at').first()
            if latest_analysis:
                progress = [
                    latest_analysis.content_score or 0,     # Ideas/Content (index 0)
                    latest_analysis.structure_score or 0,   # Organization (index 1)
                    latest_analysis.clarity_score or 0,     # Style/Clarity (index 2)
                    latest_analysis.grammar_score or 0      # Grammar (index 3)
                ]
        
        # Get pending teacher requests count
        from accounts.models import TeacherAssignmentRequest, StudentTeacherAssignment
        from assignments.models import Assignment, AssignmentSubmission
        
        pending_requests_count = TeacherAssignmentRequest.objects.filter(
            student=request.user,
            status='pending'
        ).count()
        
        # Get assignments from assigned teachers
        teacher_assignments = StudentTeacherAssignment.objects.filter(
            student=request.user
        ).select_related('teacher')
        
        teacher_ids = [ta.teacher.id for ta in teacher_assignments]
        
        # Get active assignments from assigned teachers
        available_assignments = Assignment.objects.filter(
            teacher_id__in=teacher_ids,
            is_active=True,
            due_date__gte=timezone.now()
        ).order_by('due_date')[:5]
        
        # Get submitted assignments
        submitted_assignments = AssignmentSubmission.objects.filter(
            student=request.user
        ).select_related('assignment')
        
        submitted_assignment_ids = {sub.assignment.id for sub in submitted_assignments}
        
        # Filter out already submitted assignments
        pending_assignments = [
            assignment for assignment in available_assignments 
            if assignment.id not in submitted_assignment_ids
        ]
        
        context = {
            'recent_submissions': recent_submissions,
            'total_essays': total_essays,
            'average_score': round(avg_score, 1),
            'progress_data': progress_data,
            'progress': progress,
            'ideas_progress': progress[0] if progress else 0,
            'organization_progress': progress[1] if progress else 0,
            'style_progress': progress[2] if progress else 0,
            'grammar_progress': progress[3] if progress else 0,
            'pending_assignments': len(pending_assignments),
            'available_assignments': pending_assignments,
            'essays_with_feedback': essays_with_feedback,
            'pending_requests_count': pending_requests_count,
        }
        
        return render(request, 'essays/student/dashboard.html', context)
        
    except Exception as e:
        logger.error(f"Error in student dashboard: {e}")
        messages.error(request, 'Error loading dashboard. Please try again.')
        return render(request, 'essays/student/dashboard.html', {'error': True})


@login_required
@role_required('student')
def upload(request):
    """Essay upload view"""
    assignment_id = request.GET.get('assignment_id')
    assignment = None
    
    # Get assignment details if assignment_id is provided
    if assignment_id:
        try:
            from assignments.models import Assignment
            assignment = Assignment.objects.get(id=assignment_id)
        except:
            pass  # Assignment not found, continue without it
    
    if request.method == 'POST':
        try:
            # Check if this is a text submission or file upload
            is_text_submission = request.POST.get('is_text_submission') == 'true'
            
            if is_text_submission:
                # Handle text submission
                form = EssayTextForm(request.POST)
                if form.is_valid():
                    essay_text = form.cleaned_data['essay_text']
                    essay_type = form.cleaned_data['essay_type']
                    title = request.POST.get('title', 'Untitled Essay')
                    
                    # Validate text length
                    if len(essay_text) < 50:
                        messages.error(request, 'Essay must be at least 50 characters long.')
                        return render(request, 'essays/student/upload.html', {
                            'form': EssayUploadForm(),
                            'text_form': form,
                            'assignment': assignment
                        })
                    
                    if len(essay_text) > 10000:
                        messages.error(request, 'Essay must be less than 10,000 characters.')
                        return render(request, 'essays/student/upload.html', {
                            'form': EssayUploadForm(),
                            'text_form': form,
                            'assignment': assignment
                        })
                    
                    # Sanitize text
                    essay_text = sanitize_text(essay_text)
                    
                    # Analyze with AI
                    analysis_result = analyze_essay_with_ai(essay_text, essay_type)
                    
                    # Save to database
                    analysis = save_analysis_to_database(request.user, essay_text, essay_type, analysis_result)
                    
                    # Create submission record with text indicator
                    submission = StudentSubmission.objects.create(
                        student=request.user,
                        analysis=analysis,
                        file_name=f"{title}.txt"
                    )
                    
                    # Generate checklist
                    checklist_data = generate_step_wise_checklist(analysis_result, essay_type)
                    save_checklist_progress(request.user, analysis, checklist_data)
                    
                    messages.success(request, 'Essay analyzed successfully!')
                    return redirect('essays:view_essay', analysis_id=analysis.id)
                else:
                    messages.error(request, 'Please correct the errors in your submission.')
            else:
                # Handle file upload
                form = EssayUploadForm(request.POST, request.FILES)
                if form.is_valid():
                    uploaded_file = request.FILES['essay_file']
                    essay_type = form.cleaned_data['essay_type']
                    title = request.POST.get('title', 'Untitled Essay')
                    
                    # Validate file
                    is_valid, error_message = validate_file_upload(uploaded_file)
                    if not is_valid:
                        messages.error(request, error_message)
                        return render(request, 'essays/student/upload.html', {
                            'form': form,
                            'text_form': EssayTextForm(),
                            'assignment': assignment
                        })
                    
                    # Extract text
                    essay_text = extract_text_from_file(uploaded_file)
                    
                    # Analyze with AI
                    analysis_result = analyze_essay_with_ai(essay_text, essay_type)
                    
                    # Save to database
                    analysis = save_analysis_to_database(request.user, essay_text, essay_type, analysis_result)
                    
                    # Create submission record
                    submission = StudentSubmission.objects.create(
                        student=request.user,
                        analysis=analysis,
                        file_name=uploaded_file.name
                    )
                    
                    # Generate checklist
                    checklist_data = generate_step_wise_checklist(analysis_result, essay_type)
                    save_checklist_progress(request.user, analysis, checklist_data)
                    
                    messages.success(request, 'Essay uploaded and analyzed successfully!')
                    return redirect('essays:view_essay', analysis_id=analysis.id)
                else:
                    messages.error(request, 'Please correct the errors in your submission.')
                    
        except Exception as e:
            logger.error(f"Error processing essay upload: {e}")
            messages.error(request, 'Error processing your essay. Please try again.')
    
    # GET request or error in POST - show forms
    return render(request, 'essays/student/upload.html', {
        'form': EssayUploadForm(),
        'text_form': EssayTextForm(),
        'assignment': assignment
    })


@login_required
@role_required('student')
def paste_text(request):
    """Essay text paste view"""
    if request.method == 'POST':
        form = EssayTextForm(request.POST)
        if form.is_valid():
            try:
                essay_text = sanitize_text(form.cleaned_data['essay_text'])
                essay_type = form.cleaned_data['essay_type']
                
                # Validate text length
                if len(essay_text) < 50:
                    messages.error(request, 'Essay text is too short. Minimum 50 characters required.')
                    return render(request, 'essays/student/paste_text.html', {'form': form})
                
                # Analyze with AI
                analysis_result = analyze_essay_with_ai(essay_text, essay_type)
                
                # Save to database
                analysis = save_analysis_to_database(request.user, essay_text, essay_type, analysis_result)
                
                # Create submission record
                submission = StudentSubmission.objects.create(
                    student=request.user,
                    analysis=analysis,
                    file_name='Pasted Text'
                )
                
                # Generate checklist
                checklist_data = generate_step_wise_checklist(analysis_result, essay_type)
                save_checklist_progress(request.user, analysis, checklist_data)
                
                messages.success(request, 'Essay analyzed successfully!')
                return redirect('essays:view_essay', analysis_id=analysis.id)
                
            except Exception as e:
                logger.error(f"Error processing pasted text: {e}")
                messages.error(request, 'Error analyzing your essay. Please try again.')
    else:
        form = EssayTextForm()
    
    return render(request, 'essays/student/paste_text.html', {'form': form})


@login_required
def view_essay(request, analysis_id):
    """View essay analysis results"""
    try:
        analysis = get_object_or_404(EssayAnalysis, id=analysis_id)
        
        # Check permissions
        if not (request.user == analysis.student or 
                (request.user.role == 'teacher' and 
                 request.user.student_assignments.filter(student=analysis.student).exists())):
            messages.error(request, 'You do not have permission to view this essay.')
            return redirect('essays:dashboard')
        
        # Get checklist progress
        checklist_progress = ChecklistProgress.objects.filter(
            student=analysis.student,
            analysis=analysis
        ).first()
        
        # Get teacher feedback
        teacher_feedback = getattr(analysis, 'teacher_feedback', None)
        
        # Format essay data for template compatibility
        essay_data = [
            analysis.id,  # essay[0] - id
            f"Essay Analysis #{analysis.id}",  # essay[1] - title
            analysis.essay_text,  # essay[2] - text
            analysis.essay_type,  # essay[3] - type
        ]
        
        # Prepare analysis data for JavaScript in the format expected by the template
        import json
        
        # Get the data from the analysis object and detailed_feedback
        detailed_feedback = analysis.detailed_feedback
        
        analysis_data = {
            'analysis_id': analysis.id,
            'tagged_essay': detailed_feedback.get('tagged_essay', analysis.essay_text),
            'suggestions': analysis.suggestions if isinstance(analysis.suggestions, list) else [],
            'scores': detailed_feedback.get('scores', {
                'ideas': int(analysis.content_score),
                'organization': int(analysis.structure_score),
                'style': int(analysis.clarity_score),
                'grammar': int(analysis.grammar_score)
            }),
            'score_reasons': detailed_feedback.get('score_reasons', {
                'ideas': detailed_feedback.get('content', f'Content score: {int(analysis.content_score)}/20'),
                'organization': detailed_feedback.get('structure', f'Organization score: {int(analysis.structure_score)}/25'),
                'style': detailed_feedback.get('clarity', f'Style score: {int(analysis.clarity_score)}/25'),
                'grammar': detailed_feedback.get('grammar', f'Grammar score: {int(analysis.grammar_score)}/30')
            }),
            'checklist_steps': detailed_feedback.get('checklist_steps', [])
        }
        
        # Convert to JSON string for safe template rendering
        analysis_data_json = json.dumps(analysis_data)
        
        context = {
            'analysis': analysis,
            'essay': essay_data,  # Add essay data in expected format
            'analysis_data_json': analysis_data_json,  # Add JSON string
            'checklist_progress': checklist_progress,
            'teacher_feedback': teacher_feedback,
        }
        
        return render(request, 'essays/student/view_essay.html', context)
        
    except Exception as e:
        logger.error(f"Error viewing essay: {e}")
        messages.error(request, 'Error loading essay analysis.')
        return redirect('essays:dashboard')


@login_required
@role_required('student')
def essays_list(request):
    """List all student's essays"""
    try:
        submissions = StudentSubmission.objects.filter(
            student=request.user
        ).select_related('analysis').order_by('-submitted_at')
        
        # Calculate statistics
        total_essays = submissions.count()
        scored_essays = submissions.filter(analysis__overall_score__isnull=False)
        essays_with_feedback = submissions.filter(analysis__teacher_feedback__isnull=False)
        
        # Calculate average score
        average_score = None
        if scored_essays.exists():
            total_score = sum([s.analysis.overall_score for s in scored_essays if s.analysis and s.analysis.overall_score])
            average_score = total_score / scored_essays.count() if scored_essays.count() > 0 else 0
        
        # Pagination
        paginator = Paginator(submissions, 10)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        # Backwards compatibility: some legacy templates expected an "essays" list of tuples.
        # We'll supply it so either template variant works. Tuple format (id, title, type, overall_score, submitted_at, status, has_feedback, content, structure, clarity, grammar)
        essays_legacy = []
        for s in submissions:
            a = s.analysis
            if not a:
                continue
            essays_legacy.append((
                a.id,
                s.file_name or f"Essay Analysis #{a.id}",
                a.essay_type,
                a.overall_score,
                s.submitted_at,
                'reviewed' if getattr(a, 'teacher_feedback', None) else 'analyzed',
                bool(getattr(a, 'teacher_feedback', None)),
                a.content_score,
                a.structure_score,
                a.clarity_score,
                a.grammar_score,
            ))

        # Get assignment context for essays that are part of assignments
        from assignments.models import AssignmentSubmission
        assignment_submissions = AssignmentSubmission.objects.filter(
            student=request.user
        ).select_related('assignment', 'essay_analysis')
        
        assignment_context = {}
        for asub in assignment_submissions:
            if asub.essay_analysis:
                assignment_context[asub.essay_analysis.id] = {
                    'title': asub.assignment.title,
                    'type': asub.assignment.essay_type,
                    'due_date': asub.assignment.due_date
                }

        context = {
            'page_obj': page_obj,
            'essays': essays_legacy,
            'total_essays': total_essays,
            'average_score': average_score,
            'essays_with_feedback_count': essays_with_feedback.count(),
            'scored_essays_count': scored_essays.count(),
            'assignment_context': assignment_context,
        }
        
        logger.info(f"Essays list context: essays count={len(essays_legacy)}, page_obj={page_obj.object_list.count() if page_obj else 0}")
        return render(request, 'essays/student/essays.html', context)
        
    except Exception as e:
        logger.error(f"Error loading essays list: {e}")
        messages.error(request, 'Error loading essays.')
        return render(request, 'essays/student/essays.html', {'error': True})


@login_required
@role_required('student')
def progress(request):
    """Student progress view"""
    try:
        # Get all progress records
        progress_records = ChecklistProgress.objects.filter(
            student=request.user
        ).select_related('analysis').order_by('-last_updated')
        
        # Get all essay submissions with analysis
        submissions = StudentSubmission.objects.filter(
            student=request.user
        ).select_related('analysis').order_by('-submitted_at')
        
        # Calculate overall progress
        if progress_records:
            overall_progress = sum(p.progress_percentage for p in progress_records) / len(progress_records)
        else:
            overall_progress = 0
        
        # Calculate statistics for template
        total_essays = submissions.count()
        avg_score = 0
        best_score = 0
        improvement = 0
        
        if submissions:
            scores = [s.analysis.overall_score for s in submissions if s.analysis and s.analysis.overall_score]
            if scores:
                avg_score = sum(scores) / len(scores)
                best_score = max(scores)
                if len(scores) >= 2:
                    improvement = scores[0] - scores[-1]  # First - Last (reversed order)
        
        # Calculate category averages
        content_avg = clarity_avg = structure_avg = grammar_avg = 0
        if submissions:
            content_scores = [s.analysis.content_score for s in submissions if s.analysis and s.analysis.content_score]
            clarity_scores = [s.analysis.clarity_score for s in submissions if s.analysis and s.analysis.clarity_score]
            structure_scores = [s.analysis.structure_score for s in submissions if s.analysis and s.analysis.structure_score]
            grammar_scores = [s.analysis.grammar_score for s in submissions if s.analysis and s.analysis.grammar_score]
            
            if content_scores:
                content_avg = sum(content_scores) / len(content_scores)
            if clarity_scores:
                clarity_avg = sum(clarity_scores) / len(clarity_scores)
            if structure_scores:
                structure_avg = sum(structure_scores) / len(structure_scores)
            if grammar_scores:
                grammar_avg = sum(grammar_scores) / len(grammar_scores)
        
        # Prepare progress data for charts - recent 10 submissions
        progress_data = []
        chart_data = []
        if submissions:
            recent_submissions = submissions[:10]  # Get most recent 10
            for i, submission in enumerate(reversed(recent_submissions)):  # Reverse for chronological order
                if submission.analysis and submission.analysis.overall_score:
                    progress_data.append([
                        submission.submitted_at.isoformat(),
                        submission.analysis.overall_score
                    ])
                    chart_data.append({
                        'date': submission.submitted_at.strftime('%m/%d'),
                        'score': submission.analysis.overall_score,
                        'content': submission.analysis.content_score or 0,
                        'structure': submission.analysis.structure_score or 0,
                        'clarity': submission.analysis.clarity_score or 0,
                        'grammar': submission.analysis.grammar_score or 0,
                    })
        
        # Get recent assignment submissions
        from assignments.models import AssignmentSubmission
        assignment_submissions = AssignmentSubmission.objects.filter(
            student=request.user
        ).select_related('assignment', 'essay_analysis').order_by('-submitted_at')[:5]

        context = {
            'progress_records': progress_records,
            'overall_progress': round(overall_progress, 1),
            'submissions': submissions,
            'progress_data': progress_data,
            'chart_data': chart_data,
            'assignment_submissions': assignment_submissions,
            'stats': {
                'total_essays': total_essays,
                'avg_score': round(avg_score, 1),
                'best_score': round(best_score, 1),
                'improvement': round(improvement, 1),
                'content_avg': round(content_avg, 1),
                'clarity_avg': round(clarity_avg, 1),
                'structure_avg': round(structure_avg, 1),
                'grammar_avg': round(grammar_avg, 1),
            }
        }
        
        return render(request, 'essays/student/progress.html', context)
        
    except Exception as e:
        logger.error(f"Error loading progress: {e}")
        messages.error(request, 'Error loading progress data.')
        return render(request, 'essays/student/progress.html', {'error': True})


@login_required
def update_checklist_progress(request):
    """AJAX endpoint to update checklist progress"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            progress_id = data.get('progress_id')
            completed_items = data.get('completed_items', [])
            
            progress = get_object_or_404(ChecklistProgress, id=progress_id, student=request.user)
            
            # Update completed items
            progress.completed_items = completed_items
            
            # Calculate progress percentage
            total_steps = progress.checklist_data.get('total_steps', 0)
            if total_steps > 0:
                progress.progress_percentage = (len(completed_items) / total_steps) * 100
            else:
                progress.progress_percentage = 0
            
            progress.save()
            
            return JsonResponse({
                'success': True,
                'progress_percentage': round(progress.progress_percentage, 1)
            })
            
        except Exception as e:
            logger.error(f"Error updating checklist progress: {e}")
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


@login_required
def download_suggestions(request, analysis_id):
    """Download essay suggestions as Word document"""
    try:
        analysis = get_object_or_404(EssayAnalysis, id=analysis_id)
        
        # Check permissions
        if not (request.user == analysis.student or 
                (request.user.role == 'teacher' and 
                 request.user.student_assignments.filter(student=analysis.student).exists())):
            messages.error(request, 'You do not have permission to download this document.')
            return redirect('essays:dashboard')
        
        # Create Word document with enhanced formatting
        doc_io = create_word_document_with_suggestions(
            analysis.essay_text,
            analysis.suggestions,
            f"suggestions_{analysis.id}",
            analysis  # Pass the analysis object for scores and feedback
        )
        
        # Return as download
        response = HttpResponse(
            doc_io.read(),
            content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
        response['Content-Disposition'] = f'attachment; filename="essay_suggestions_{analysis.id}.docx"'
        
        return response
        
    except Exception as e:
        logger.error(f"Error downloading suggestions: {e}")
        messages.error(request, 'Error downloading suggestions.')
        return redirect('essays:view_essay', analysis_id=analysis_id)


@login_required
def accept_suggestion(request):
    """API endpoint to accept a word-level suggestion"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        suggestion_id = data.get('suggestion_id')
        suggestion_type = data.get('type')
        text = data.get('text')
        
        # For now, just return success - in a full implementation, 
        # you would save this to the database
        logger.info(f"Suggestion accepted: {suggestion_id} - {suggestion_type} - {text}")
        
        return JsonResponse({
            'success': True,
            'message': 'Suggestion accepted successfully'
        })
        
    except Exception as e:
        logger.error(f"Error accepting suggestion: {e}")
        return JsonResponse({'error': 'Failed to accept suggestion'}, status=500)


@login_required  
def reject_suggestion(request):
    """API endpoint to reject a word-level suggestion"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        suggestion_id = data.get('suggestion_id')
        suggestion_type = data.get('type')
        text = data.get('text')
        
        # For now, just return success - in a full implementation,
        # you would save this to the database
        logger.info(f"Suggestion rejected: {suggestion_id} - {suggestion_type} - {text}")
        
        return JsonResponse({
            'success': True,
            'message': 'Suggestion rejected successfully'
        })
        
    except Exception as e:
        logger.error(f"Error rejecting suggestion: {e}")
        return JsonResponse({'error': 'Failed to reject suggestion'}, status=500)
