from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError

# Create your models here.
class Employee(AbstractUser):
    '''Custom user model for employees'''
    ROLES = [
        ('MANAGER', 'Manager'),
        ('SALES', 'Sales'),
        ('INVENTORY', 'Inventory'),
    ]

    role = models.CharField(max_length=20, choices=ROLES)
    phone = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date_joined']
        verbose_name = 'Employee'
        verbose_name_plural = 'Employees'
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
    
    def clean(self):
        super().clean()
        if self.phone and not self.phone.replace('+', '').replace(' ', '').isdigit():
            raise ValidationError({'phone': 'Phone number must contain only digits.'})
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.username
