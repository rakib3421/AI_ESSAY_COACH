from django.urls import path
from . import views

app_name = 'analytics'

urlpatterns = [
    path('dashboard/', views.teacher_dashboard, name='teacher_dashboard'),
    path('students/', views.students_list, name='students_list'),
    path('student/<int:student_id>/', views.student_detail, name='student_detail'),
    path('analytics/', views.analytics_overview, name='analytics_overview'),
    path('assignment/<int:assignment_id>/', views.assignment_analytics, name='assignment_analytics'),
    path('export/', views.export_analytics_data, name='export_analytics_data'),
]
