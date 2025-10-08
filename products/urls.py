from django.urls import path
from . import views

app_name = 'products'

urlpatterns = [
    path('', views.product_list, name='product_list'),  # Keep as-is
    path('create/', views.create_product, name='create_product'),  # Keep as-is
    path('<int:pk>/', views.product_detail, name='product_detail'),  # Keep as-is
    path('<int:pk>/update/', views.update_product, name='update_product'),  # ADD THIS
    path('<int:pk>/delete/', views.delete_product, name='delete_product'),  # ADD THIS
    
    # Category and Unit URLs
    path('settings/', views.category_unit_list, name='category_unit_list'),  # ADD THIS
    path('categories/create/', views.create_category, name='create_category'),  # ADD THIS
    path('categories/<int:pk>/update/', views.update_category, name='update_category'),  # ADD THIS
    path('categories/<int:pk>/delete/', views.delete_category, name='delete_category'),  # ADD THIS
    path('units/create/', views.create_unit, name='create_unit'),  # ADD THIS
    path('units/<int:pk>/update/', views.update_unit, name='update_unit'),  # ADD THIS
    path('units/<int:pk>/delete/', views.delete_unit, name='delete_unit'),  # ADD THIS
]