from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    # Stock Management
    path('', views.stock_list, name='stock_list'),
    path('entry/', views.stock_entry, name='stock_entry'),
    
    # Dashboard and Reports
    path('dashboard/', views.inventory_dashboard, name='dashboard'),
    path('reports/', views.inventory_reports, name='reports'),
    
    # Stock Movements (Audit Trail)
    path('movements/', views.stock_movements, name='stock_movements'),
]