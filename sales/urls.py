from django.urls import path
from . import views

app_name = 'sales'

urlpatterns = [
    path('', views.sale_list, name='sale_list'),  # Keep as-is
    path('create/', views.create_sale, name='create_sale'),  # Keep as-is
    path('<int:pk>/', views.sale_detail, name='sale_detail'),  # Keep as-is
    path('<int:pk>/complete/', views.complete_sale, name='complete_sale'),  # Keep as-is
    path('<int:pk>/cancel/', views.cancel_sale, name='cancel_sale'),  # ADD THIS
    path('<int:pk>/delete/', views.delete_sale, name='delete_sale'),  # ADD THIS
    
    # Customer URLs
    path('customers/', views.customer_list, name='customer_list'),  # Keep as-is
    path('customers/create/', views.create_customer, name='create_customer'),  # Keep as-is
    path('customers/<int:pk>/update/', views.update_customer, name='update_customer'),  # ADD THIS
    path('customers/<int:pk>/delete/', views.delete_customer, name='delete_customer'),  # ADD THIS
    
    # Reports
    path('reports/', views.sales_reports, name='reports'),  # Keep as-is
    path('dashboard/', views.sales_dashboard, name='dashboard'),  # Keep as-is
]