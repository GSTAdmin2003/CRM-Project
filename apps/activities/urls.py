from django.urls import path
from . import views

app_name = 'activities'

urlpatterns = [
    # Dashboard
    path('', views.activity_dashboard, name='dashboard'),

    # Activity CRUD
    path('create/', views.activity_create, name='activity_create'),
    path('<int:pk>/', views.activity_detail, name='activity_detail'),
    path('<int:pk>/edit/', views.activity_edit, name='activity_edit'),
    path('<int:pk>/delete/', views.activity_delete, name='activity_delete'),
    path('<int:pk>/complete/', views.activity_complete, name='activity_complete'),
]
