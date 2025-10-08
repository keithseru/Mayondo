from django.urls import path
from . import views

app_name = 'products'

urlpatterns = [
    # Product URLs
    path('', views.product_list, name='product_list'),
    path('create/', views.create_product, name='create_product'),
    path('<int:pk>/', views.product_detail, name='product_detail'),
    path('<int:pk>/update/', views.update_product, name='update_product'),
    path('<int:pk>/delete/', views.delete_product, name='delete_product'),
    
    # Category and Unit Management
    path('settings/', views.category_unit_list, name='category_unit_list'),
    
    # Category URLs
    path('categories/create/', views.create_category, name='create_category'),
    path('categories/<int:pk>/update/', views.update_category, name='update_category'),
    path('categories/<int:pk>/delete/', views.delete_category, name='delete_category'),
    
    # Unit URLs
    path('units/create/', views.create_unit, name='create_unit'),
    path('units/<int:pk>/update/', views.update_unit, name='update_unit'),
    path('units/<int:pk>/delete/', views.delete_unit, name='delete_unit'),
]