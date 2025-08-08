from django.contrib import admin
from .models import EssayAnalysis, StudentSubmission, ChecklistProgress, EssayFeedback


@admin.register(EssayAnalysis)
class EssayAnalysisAdmin(admin.ModelAdmin):
    list_display = ('student', 'essay_type', 'overall_score', 'created_at')
    list_filter = ('essay_type', 'created_at')
    search_fields = ('student__username', 'essay_type')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(StudentSubmission)
class StudentSubmissionAdmin(admin.ModelAdmin):
    list_display = ('student', 'file_name', 'submitted_at')
    list_filter = ('submitted_at',)
    search_fields = ('student__username', 'file_name')


@admin.register(ChecklistProgress)
class ChecklistProgressAdmin(admin.ModelAdmin):
    list_display = ('student', 'progress_percentage', 'last_updated')
    list_filter = ('last_updated',)
    search_fields = ('student__username',)


@admin.register(EssayFeedback)
class EssayFeedbackAdmin(admin.ModelAdmin):
    list_display = ('teacher', 'analysis', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('teacher__username', 'analysis__student__username')
