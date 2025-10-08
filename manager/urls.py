from django.urls import path
from . import views

app_name = 'manager'

urlpatterns = [
    path('', views.manager_dashboard, name='dashboard'),
    path('reports/', views.manager_reports, name='reports'),
]