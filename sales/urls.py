from django.urls import path
from . import views

app_name = 'sales'

urlpatterns = [
    path('', views.sale_list, name='list'),
    path('create/', views.sale_create, name='create'),
    path('<int:pk>/', views.sale_detail, name='detail'),
    path('<int:pk>/complete/', views.complete_sale, name='complete'),
]