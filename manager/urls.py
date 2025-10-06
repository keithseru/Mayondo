from django.urls import path
from . import views

app_name = 'manager'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('reports/', views.reports, name='reports'),
]