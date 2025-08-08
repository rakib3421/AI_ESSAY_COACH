from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class Assignment(models.Model):
    """Model for teacher assignments"""
    
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
    
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_assignments')
    title = models.CharField(max_length=255)
    description = models.TextField()
    essay_type = models.CharField(max_length=50, choices=ESSAY_TYPE_CHOICES)
    due_date = models.DateTimeField()
    max_score = models.FloatField(default=100.0)
    instructions = models.TextField(blank=True)
    rubric = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.title} by {self.teacher.username}"
    
    def is_overdue(self):
        return timezone.now() > self.due_date
    
    def get_submission_count(self):
        return self.submissions.count()


class AssignmentSubmission(models.Model):
    """Model for student assignment submissions"""
    
    STATUS_CHOICES = [
        ('submitted', 'Submitted'),
        ('graded', 'Graded'),
        ('returned', 'Returned'),
    ]
    
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='submissions')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='assignment_submissions')
    essay_analysis = models.ForeignKey('essays.EssayAnalysis', on_delete=models.CASCADE, null=True, blank=True)
    
    submission_text = models.TextField()
    file_name = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='submitted')
    
    submitted_at = models.DateTimeField(auto_now_add=True)
    graded_at = models.DateTimeField(null=True, blank=True)
    teacher_score = models.FloatField(null=True, blank=True)
    teacher_feedback = models.TextField(blank=True)
    
    class Meta:
        unique_together = ['assignment', 'student']
        ordering = ['-submitted_at']
        
    def __str__(self):
        return f"{self.assignment.title} - {self.student.username}"
    
    def is_late(self):
        return self.submitted_at > self.assignment.due_date
    
    def get_final_score(self):
        """Get final score combining AI and teacher scores"""
        if self.teacher_score is not None:
            return self.teacher_score
        elif self.essay_analysis:
            return self.essay_analysis.overall_score
        return 0
