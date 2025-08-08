from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('', views.index, name='index'),
    path('signup/', views.signup, name='signup'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('profile/', views.profile, name='profile'),
    path('settings/', views.settings, name='settings'),
    path('teacher-requests/', views.teacher_requests, name='teacher_requests'),
    path('accept-request/<int:request_id>/', views.accept_teacher_request, name='accept_teacher_request'),
    path('reject-request/<int:request_id>/', views.reject_teacher_request, name='reject_teacher_request'),
    
    # Teacher views
    path('teacher/add-student/', views.add_student, name='add_student'),
    path('teacher/my-students/', views.my_students, name='my_students'),
    path('teacher/student/<int:student_id>/submissions/', views.student_submissions, name='student_submissions'),
    path('teacher/feedback/<int:analysis_id>/', views.give_feedback, name='give_feedback'),
]
