from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import HttpResponse
from django.core.paginator import Paginator
import csv
from .forms import StaffForm, StaffAuthenticationForm
from .models import Employee

# Role checks
def is_manager(user):
    return user.is_authenticated and user.role == 'MANAGER'

def is_staff(user):
    return user.is_authenticated and user.role in ['MANAGER', 'SALES', 'INVENTORY']

# Login view
def login_user(request):
    if request.method == "POST":
        form = StaffAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if user.role in ["MANAGER", "SALES", "INVENTORY"]:
                login(request, user)
                return redirect('dashboard_router')
            else:
                messages.error(request, 'You are not authorized to access the system.')
                return redirect('login_user')
    else:
        form = StaffAuthenticationForm()

    context = {
        'form': form,
        'title': 'Login'
    }
    return render(request, 'users/login.html', context)

# Logout view
@login_required
def logout_user(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('login_user')

# Staff creation (manager only)
@login_required
@user_passes_test(is_manager, login_url='login_user')
def create_staff(request):
    if request.method == 'POST':
        form = StaffForm(request.POST)
        if form.is_valid():
            staff = form.save()
            messages.success(request, f'Staff account created successfully. Username: {staff.username}')
            return redirect('staff_list')
    else:
        form = StaffForm()

    context = {
        'form': form,
        'title': 'Create Staff Account'
    }
    return render(request, 'users/create_staff.html', context)

@login_required
@user_passes_test(is_manager, login_url='login_user')
def update_staff(request, pk):
    staff_user = get_object_or_404(Employee, pk=pk)
    if request.method == 'POST':
        form = StaffForm(request.POST, instance=staff_user)
        if form.is_valid():
            form.save()
            messages.success(request, "Staff user updated successfully.")
            return redirect('staff_list')
    else:
        form = StaffForm(instance=staff_user)
    return render(request, 'users/create_staff.html', {
        'form': form,
        'title': f"Edit Staff: {staff_user.username}",
        'button_label': "Update Staff User"
    })

@login_required
@user_passes_test(is_manager, login_url='login_user')
def delete_staff(request, pk):
    staff_user = get_object_or_404(Employee, pk=pk)
    if request.method == 'POST':
        staff_user.delete()
        messages.success(request, "Staff user deleted.")
        return redirect('staff_list')
    return render(request, 'users/delete_staff.html', {
        'staff_user': staff_user,
        'title': f"Delete Staff: {staff_user.username}"
    })

@login_required
@user_passes_test(is_manager, login_url='login_user')
def staff_list(request):
    role_filter = request.GET.get('role')
    joined_after = request.GET.get('joined_after')

    staff_members = Employee.objects.filter(role__in=['SALES', 'INVENTORY', 'MANAGER'])

    if role_filter:
        staff_members = staff_members.filter(role=role_filter)

    if joined_after:
        staff_members = staff_members.filter(date_joined__gte=joined_after)

    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="staff_list.csv"'
        writer = csv.writer(response)
        writer.writerow(['Name', 'Username', 'Email', 'Role', 'Date Joined', 'Last Login'])
        for staff in staff_members:
            writer.writerow([
                staff.get_full_name() or staff.username,
                staff.username,
                staff.email,
                staff.role,
                staff.date_joined.strftime('%Y-%m-%d'),
                staff.last_login.strftime('%Y-%m-%d %H:%M') if staff.last_login else '—'
            ])
        return response

    paginator = Paginator(staff_members.order_by('-date_joined'), 10)  # 10 per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'title': 'Staff Members',
        'role_filter': role_filter,
        'joined_after': joined_after
    }
    
    return render(request, 'users/staff_list.html', context)

@login_required
@user_passes_test(is_manager, login_url='login_user')
def staff_detail(request, pk):
    staff_user = get_object_or_404(Employee, pk=pk)
    return render(request, 'users/staff_detail.html', {
        'staff_user': staff_user,
        'title': f"Staff Details: {staff_user.get_full_name() or staff_user.username}"

    })


# Profile view
@login_required
def profile_view(request):
    return render(request, 'users/profile.html', {
        'user': request.user,
        'title': 'My Profile'
    })

# Dashboard router
@login_required
def dashboard_router(request):
    role = request.user.role
    if role == 'MANAGER':
        return redirect('manager_dashboard')
    elif role == 'SALES':
        return redirect('sales_dashboard')
    elif role == 'INVENTORY':
        return redirect('inventory_dashboard')
    else:
        messages.error(request, 'Invalid role. Contact admin.')
        return redirect('login_user')