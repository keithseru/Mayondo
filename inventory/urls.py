from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    path('', views.stock_list, name='stock_list'),  # Keep this one as-is
    path('entry/', views.stock_entry, name='stock_entry'),  # Keep this
    path('dashboard/', views.inventory_dashboard, name='dashboard'),  # Keep this
    path('reports/', views.inventory_reports, name='reports'),  # Keep this
]