from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Employee

# Register your models here.
@admin.register(Employee)
class EmployeeAdmin(UserAdmin):
    list_display = ['username', 'email', 'role', 'is_active', 'date_joined']
    list_filter = ['role', 'is_active']
    fieldsets = UserAdmin.fieldsets + (
        ('Additional Info', {'fields': ('role', 'phone', 'address')}),
    )