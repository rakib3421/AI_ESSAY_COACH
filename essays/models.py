from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import json

User = get_user_model()


class EssayAnalysis(models.Model):
    """Model for storing essay analysis results"""
    
    ESSAY_TYPE_CHOICES = [
        ('argumentative', 'Argumentative Essay'),
        ('expository', 'Expository Essay'),
        ('narrative', 'Narrative Essay'),
        ('descriptive', 'Descriptive Essay'),
        ('persuasive', 'Persuasive Essay'),
        ('compare_contrast', 'Compare and Contrast Essay'),
        ('cause_effect', 'Cause and Effect Essay'),
        ('process', 'Process Essay'),
        ('definition', 'Definition Essay'),
        ('classification', 'Classification Essay'),
    ]
    
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='essay_analyses')
    essay_text = models.TextField()
    essay_type = models.CharField(max_length=50, choices=ESSAY_TYPE_CHOICES)
    overall_score = models.FloatField()
    grammar_score = models.FloatField()
    clarity_score = models.FloatField()
    structure_score = models.FloatField()
    content_score = models.FloatField()
    
    # JSON fields for detailed analysis
    detailed_feedback = models.JSONField(default=dict)
    suggestions = models.JSONField(default=list)
    strengths = models.JSONField(default=list)
    areas_improvement = models.JSONField(default=list)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return f"Essay Analysis for {self.student.username} - {self.essay_type}"


class StudentSubmission(models.Model):
    """Model for tracking student submissions"""
    
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='submissions')
    analysis = models.ForeignKey(EssayAnalysis, on_delete=models.CASCADE)
    file_name = models.CharField(max_length=255, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-submitted_at']
        
    def __str__(self):
        return f"Submission by {self.student.username} at {self.submitted_at}"


class ChecklistProgress(models.Model):
    """Model for tracking student progress on improvement checklists"""
    
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    analysis = models.ForeignKey(EssayAnalysis, on_delete=models.CASCADE)
    checklist_data = models.JSONField(default=dict)
    completed_items = models.JSONField(default=list)
    progress_percentage = models.FloatField(default=0.0)
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['student', 'analysis']
        
    def __str__(self):
        return f"Progress for {self.student.username} - {self.progress_percentage}%"


class EssayFeedback(models.Model):
    """Model for teacher feedback on essays"""
    
    analysis = models.OneToOneField(EssayAnalysis, on_delete=models.CASCADE, related_name='teacher_feedback')
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name='given_feedback')
    feedback_text = models.TextField()
    additional_score = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Feedback by {self.teacher.username} for {self.analysis.student.username}"
