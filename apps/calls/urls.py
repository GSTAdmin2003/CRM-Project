from django.urls import path
from . import views

app_name = 'calls'

urlpatterns = [
    # Main views
    path('', views.call_list, name='call_list'),
    path('dialpad/', views.dialpad, name='dialpad'),
    path('<int:pk>/', views.call_detail, name='call_detail'),

    # Call actions
    path('initiate/', views.initiate_call, name='initiate_call'),
    path('<int:pk>/hangup/', views.hangup_call, name='hangup_call'),
    path('<int:pk>/answer/', views.answer_call, name='answer_call'),
    path('<int:pk>/status/', views.call_status, name='call_status'),

    # Call management
    path('<int:pk>/notes/', views.update_call_notes, name='update_call_notes'),
    path('<int:pk>/link-contact/', views.link_call_to_contact, name='link_call_to_contact'),
    path('<int:pk>/link-opportunity/', views.link_call_to_opportunity, name='link_call_to_opportunity'),

    # Recording
    path('recording/<int:pk>/download/', views.recording_download, name='recording_download'),

    # API
    path('api/active/', views.active_calls, name='active_calls'),
]
