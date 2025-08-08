from django.contrib import admin
from .models import Assignment, AssignmentSubmission


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ('title', 'teacher', 'essay_type', 'due_date', 'is_active', 'created_at')
    list_filter = ('essay_type', 'is_active', 'created_at', 'due_date')
    search_fields = ('title', 'teacher__username', 'description')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(AssignmentSubmission)
class AssignmentSubmissionAdmin(admin.ModelAdmin):
    list_display = ('assignment', 'student', 'status', 'submitted_at', 'teacher_score')
    list_filter = ('status', 'submitted_at', 'graded_at')
    search_fields = ('assignment__title', 'student__username')
    readonly_fields = ('submitted_at', 'graded_at')
