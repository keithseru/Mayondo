# users/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import Employee

class StaffForm(UserCreationForm):
    role = forms.ChoiceField(choices=Employee.ROLES)

    class Meta:
        model = Employee
        fields = ['username', 'first_name', 'last_name', 'email', 'phone', 'role', 'password1', 'password2']
        labels = {
            'phone': 'Phone Number',
        }
        help_texts = {
            'username': 'Choose a unique username.',
            'password1': 'Minimum 8 characters.',
        }

class StaffAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        label='Username',
        widget=forms.TextInput(attrs={'placeholder': 'Enter username', 'class': 'form-control'})
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={'placeholder': 'Enter password', 'class': 'form-control'})
    )