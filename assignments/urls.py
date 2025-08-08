from django.urls import path
from . import views

app_name = 'assignments'

urlpatterns = [
    path('create/', views.create_assignment, name='create_assignment'),
    path('edit/<int:assignment_id>/', views.edit_assignment, name='edit_assignment'),
    path('detail/<int:assignment_id>/', views.assignment_detail, name='assignment_detail'),
    path('submit/<int:assignment_id>/', views.submit_assignment, name='submit_assignment'),
    path('submissions/<int:assignment_id>/', views.assignment_submissions, name='assignment_submissions'),
    path('grade/<int:submission_id>/', views.grade_submission, name='grade_submission'),
    path('list/', views.assignments_list, name='assignments_list'),
    path('student/', views.student_assignments, name='student_assignments'),
]
