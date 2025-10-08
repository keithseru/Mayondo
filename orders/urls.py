from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    path('', views.order_list, name='order_list'),  # Keep as-is
    path('create/', views.create_order, name='create_order'),  # Keep as-is
    path('<int:pk>/', views.order_detail, name='order_detail'),  # Keep as-is
    path('<int:pk>/confirm-delivery/', views.confirm_delivery, name='confirm_delivery'),  # ADD THIS
    path('<int:pk>/delete/', views.delete_order, name='delete_order'),  # ADD THIS
    
    # Supplier URLs
    path('suppliers/', views.supplier_list, name='supplier_list'),  # ADD THIS
    path('suppliers/create/', views.create_supplier, name='create_supplier'),  # ADD THIS
    path('suppliers/<int:pk>/update/', views.update_supplier, name='update_supplier'),  # ADD THIS
    path('suppliers/<int:pk>/delete/', views.delete_supplier, name='delete_supplier'),  # ADD THIS
]