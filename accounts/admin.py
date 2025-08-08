from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, StudentTeacherAssignment, TeacherAssignmentRequest


class CustomUserAdmin(UserAdmin):
    """Custom admin for CustomUser"""
    list_display = ('username', 'email', 'role', 'is_active', 'date_joined')
    list_filter = ('role', 'is_active', 'date_joined')
    search_fields = ('username', 'email')
    
    fieldsets = UserAdmin.fieldsets + (
        ('Role Information', {'fields': ('role',)}),
    )
    
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Role Information', {'fields': ('role',)}),
    )


@admin.register(StudentTeacherAssignment)
class StudentTeacherAssignmentAdmin(admin.ModelAdmin):
    """Admin for StudentTeacherAssignment"""
    list_display = ('student', 'teacher', 'assigned_at')
    list_filter = ('assigned_at',)
    search_fields = ('student__username', 'teacher__username')


@admin.register(TeacherAssignmentRequest)
class TeacherAssignmentRequestAdmin(admin.ModelAdmin):
    """Admin for TeacherAssignmentRequest"""
    list_display = ('teacher', 'student', 'status', 'created_at', 'responded_at')
    list_filter = ('status', 'created_at')
    search_fields = ('teacher__username', 'student__username')
    readonly_fields = ('created_at', 'responded_at')


admin.site.register(CustomUser, CustomUserAdmin)
