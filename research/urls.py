from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),

    path('project/<int:project_id>/', views.project_detail,
         name='project'),

    path('research/<int:research_id>/', views.research_detail,
         name='research_detail'),

    path('project/<int:project_id>/combined/',
         views.combined, name='combined'),

    path('project/<int:project_id>/pdf/',
         views.export_pdf, name='export_pdf'),
]
