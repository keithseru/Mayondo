from django.urls import path
from . import views

app_name = 'sales'

urlpatterns = [
    path('', views.sale_list, name='sale_list'),
    path('create/', views.create_sale, name='create_sale'), 
    path('<int:pk>/', views.sale_detail, name='sale_detail'),
    path('<int:pk>/complete/', views.complete_sale, name='complete_sale'),
    path('<int:pk>/cancel/', views.cancel_sale, name='cancel_sale'),
    path('<int:pk>/delete/', views.delete_sale, name='delete_sale'),
    
    # Customer URLs
    path('customers/', views.customer_list, name='customer_list'),
    path('customers/create/', views.create_customer, name='create_customer'),
    path('customers/<int:pk>/update/', views.update_customer, name='update_customer'),
    path('customers/<int:pk>/delete/', views.delete_customer, name='delete_customer'),
    
    # Reports
    path('reports/', views.sales_reports, name='reports'),
    path('dashboard/', views.sales_dashboard, name='dashboard'),
]