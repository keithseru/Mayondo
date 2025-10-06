from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    path('', views.stock_list, name='list'),
    path('entry/', views.stock_entry, name='entry'),
    path('dashboard/', views.dashboard, name='dashboard'),
]