from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    """Extended User model with role-based authentication"""
    
    ROLE_CHOICES = [
        ('student', 'Student'),
        ('teacher', 'Teacher'),
    ]
    
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='student')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.username} ({self.role})"
    
    def is_student(self):
        return self.role == 'student'
    
    def is_teacher(self):
        return self.role == 'teacher'


class StudentTeacherAssignment(models.Model):
    """Model to manage student-teacher relationships"""
    
    student = models.ForeignKey(
        CustomUser, 
        on_delete=models.CASCADE, 
        related_name='teacher_assignments',
        limit_choices_to={'role': 'student'}
    )
    teacher = models.ForeignKey(
        CustomUser, 
        on_delete=models.CASCADE, 
        related_name='student_assignments',
        limit_choices_to={'role': 'teacher'}
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['student', 'teacher']
        
    def __str__(self):
        return f"{self.student.username} assigned to {self.teacher.username}"


class TeacherAssignmentRequest(models.Model):
    """Model for teacher assignment requests to students"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ]
    
    teacher = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='sent_requests',
        limit_choices_to={'role': 'teacher'}
    )
    student = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='received_requests',
        limit_choices_to={'role': 'student'}
    )
    message = models.TextField(blank=True, help_text="Optional message from teacher")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ['teacher', 'student']
        ordering = ['-created_at']
        
    def __str__(self):
        return f"Request from {self.teacher.username} to {self.student.username} - {self.status}"
