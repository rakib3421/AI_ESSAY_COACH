from django.urls import path
from . import views

app_name = 'essays'

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('upload/', views.upload, name='upload'),
    path('paste/', views.paste_text, name='paste_text'),
    path('view/<int:analysis_id>/', views.view_essay, name='view_essay'),
    path('list/', views.essays_list, name='essays_list'),
    path('progress/', views.progress, name='progress'),
    path('update-progress/', views.update_checklist_progress, name='update_progress'),
    path('download/<int:analysis_id>/', views.download_suggestions, name='download_suggestions'),
    # API endpoints for suggestion actions
    path('api/suggestions/accept/', views.accept_suggestion, name='accept_suggestion'),
    path('api/suggestions/reject/', views.reject_suggestion, name='reject_suggestion'),
]
