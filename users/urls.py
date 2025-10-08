from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    path('login/', views.login_user, name='login'),
    path('logout/', views.logout_user, name='logout'),
    path('dashboard/', views.dashboard_router, name='dashboard'),
    
    # Staff Management
    path('profile/', views.profile_view, name='profile'),
    path('staff_list/', views.staff_list, name='staff_list'),
    path('staff/create/', views.create_staff, name='create_staff'),
    path('staff/<int:pk>/', views.staff_detail, name='staff_detail'),
    path('staff/<int:pk>/edit/', views.update_staff, name='update_staff'),
    path('staff/<int:pk>/delete/', views.delete_staff, name='delete_staff'),
]