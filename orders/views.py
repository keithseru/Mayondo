from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.db import transaction
from django.utils import timezone
import csv
from .models import Order, Supplier, OrderItem
from .forms import OrderForm, OrderItemFormSet, DeliveryFormSet, SupplierForm

# Create your views here

def is_manager(user):
    return user.is_authenticated and user.role == 'MANAGER'

def is_inventory_or_manager(user):
    return user.is_authenticated and user.role in ['INVENTORY', 'MANAGER']

# Orders
@login_required
@user_passes_test(is_inventory_or_manager, login_url='users:login')
def order_list(request):
    status_filter = request.GET.get('status')
    supplier_filter = request.GET.get('supplier')
    date_filter = request.GET.get('ordered_after')
    export = request.GET.get('export')

    orders = Order.objects.select_related('supplier', 'created_by', 'received_by')

    if status_filter:
        orders = orders.filter(status=status_filter)
    if supplier_filter:
        orders = orders.filter(supplier__id=supplier_filter)
    if date_filter:
        orders = orders.filter(order_date__gte=date_filter)

    if export == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="orders.csv"'
        writer = csv.writer(response)
        writer.writerow(['Order ID', 'Supplier', 'Order Date', 'Expected Delivery', 'Status', 'Total Amount', 'Received By'])
        for order in orders:
            writer.writerow([
                order.id,
                order.supplier.name,
                order.order_date.strftime('%Y-%m-%d'),
                order.expected_delivery.strftime('%Y-%m-%d') if order.expected_delivery else '—',
                order.get_status_display(),
                order.total_amount,
                order.received_by.username if order.received_by else '—'
            ])
        return response

    paginator = Paginator(orders.order_by('-order_date'), 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    suppliers = Supplier.objects.filter(is_active=True).order_by('name')

    return render(request, 'orders/order_list.html', {
        'page_obj': page_obj,
        'suppliers': suppliers,
        'status_filter': status_filter,
        'supplier_filter': supplier_filter,
        'date_filter': date_filter,
        'title': 'Purchase Orders'
    })

@login_required
@user_passes_test(is_manager, login_url="users:login")
def create_order(request):
    if request.method == "POST":
        form = OrderForm(request.POST)
        formset = OrderItemFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                order = form.save(commit=False)
                order.created_by = request.user
                order.status = 'PENDING'
                order.save()
                
                items = formset.save(commit=False)
                for item in items:
                    item.order = order
                    item.save()
                
                messages.success(
                    request, 
                    f"Order #{order.id} created successfully. Total: UGX {order.total_amount:,}"
                )
                return redirect('orders:order_detail', pk=order.pk)
    else:
        form = OrderForm()
        formset = OrderItemFormSet()

    context = {
        'form': form,
        'formset': formset,
        'title': 'Create Purchase Order'
    }
    return render(request, 'orders/create_order.html', context)

@login_required
@user_passes_test(is_inventory_or_manager, login_url="users:login")
def confirm_delivery(request, pk):
    order = get_object_or_404(Order, pk=pk)
    
    if order.status == 'DELIVERED':
        messages.warning(request, 'This order has already been fully delivered.')
        return redirect('orders:order_detail', pk=pk)

    if request.method == 'POST':
        formset = DeliveryFormSet(request.POST, queryset=order.items.all())
        
        if formset.is_valid():
            with transaction.atomic():
                # Track if any deliveries were made
                has_delivery = False
                errors = []
                
                for form in formset:
                    # Skip forms that don't have an instance (shouldn't happen with extra=0)
                    if not form.instance or not form.instance.pk:
                        continue
                    
                    delivered_qty = form.cleaned_data.get('delivered_quantity', 0) or 0
                    
                    if delivered_qty > 0:
                        has_delivery = True
                        
                        # CRITICAL FIX: Get fresh instance from database, not from form
                        item = OrderItem.objects.get(pk=form.instance.pk)
                        
                        # Validate remaining quantity using fresh data
                        if delivered_qty > item.remaining_quantity:
                            errors.append(
                                f'Cannot deliver {delivered_qty} units of {item.variant}. '
                                f'Only {item.remaining_quantity} remaining.'
                            )
                            continue
                        
                        try:
                            # Mark THIS specific item as delivered and update stock
                            item.mark_as_delivered(delivered_qty)
                        except ValueError as e:
                            errors.append(str(e))
                            continue
                
                # If there were errors, show them and don't redirect
                if errors:
                    for error in errors:
                        messages.error(request, error)
                    return redirect('orders:confirm_delivery', pk=pk)
                
                if not has_delivery:
                    messages.warning(request, 'No items were delivered. Please enter quantities greater than 0.')
                    return redirect('orders:confirm_delivery', pk=pk)
                
                # Update order status based on delivery completion
                if order.is_fully_delivered:
                    order.status = 'DELIVERED'
                    order.received_date = timezone.now()
                    messages.success(
                        request, 
                        f"Order #{order.id} fully delivered and marked as COMPLETED. Stock updated."
                    )
                elif order.is_partially_delivered:
                    order.status = 'PARTIAL'
                    messages.success(
                        request, 
                        f"Partial delivery confirmed for Order #{order.id}. Stock updated."
                    )
                
                # Set received_by if not already set
                if not order.received_by:
                    order.received_by = request.user
                
                order.save()
                
                return redirect('orders:order_detail', pk=order.pk)
        else:
            # Show formset errors
            for i, form in enumerate(formset):
                if form.errors:
                    for field, errors in form.errors.items():
                        for error in errors:
                            messages.error(request, f"Item {i+1} - {field}: {error}")
            messages.error(request, 'Please correct the errors in the form.')
    else:
        # Show ALL items, not just undelivered ones, so we can see delivery progress
        formset = DeliveryFormSet(queryset=order.items.all())

    context = {
        'order': order,
        'formset': formset,
        'title': f'Confirm Delivery - Order #{order.id}'
    }
    return render(request, 'orders/confirm_delivery.html', context)

@login_required
@user_passes_test(is_inventory_or_manager, login_url="users:login")
def order_detail(request, pk):
    order = get_object_or_404(
        Order.objects.select_related('supplier', 'created_by', 'received_by')
        .prefetch_related('items__variant__product'), 
        pk=pk
    )
    return render(request, 'orders/order_detail.html', {
        'order': order,
        'title': f"Order #{order.id} Details"
    })

@login_required
@user_passes_test(is_manager, login_url="users:login")
def delete_order(request, pk):
    order = get_object_or_404(Order, pk=pk)
    
    if order.status == 'DELIVERED':
        messages.error(request, 'Cannot delete delivered orders.')
        return redirect('orders:order_detail', pk=pk)
    
    if request.method == 'POST':
        order_id = order.id
        order.delete()
        messages.success(request, f"Order #{order_id} deleted successfully.")
        return redirect('orders:order_list')
    
    return render(request, 'orders/delete_order.html', {
        'order': order,
        'title': f"Delete Order #{order.id}"
    })

# Suppliers   
@login_required
@user_passes_test(is_inventory_or_manager, login_url='users:login')
def supplier_list(request):
    search = request.GET.get('search', '')
    
    suppliers = Supplier.objects.filter(is_active=True)
    
    if search:
        from django.db.models import Q
        suppliers = suppliers.filter(
            Q(name__icontains=search) |
            Q(contact_person__icontains=search) |
            Q(email__icontains=search) |
            Q(phone__icontains=search)
        )
    
    suppliers = suppliers.order_by('name')
    
    return render(request, 'orders/supplier_list.html', {
        'suppliers': suppliers,
        'search': search,
        'title': 'Suppliers'
    })
    
@login_required
@user_passes_test(is_inventory_or_manager, login_url='users:login')
def create_supplier(request):
    if request.method == 'POST':
        form = SupplierForm(request.POST)
        if form.is_valid():
            supplier = form.save()
            messages.success(request, f"Supplier {supplier.name} added successfully.")
            return redirect('orders:supplier_list')
    else:
        form = SupplierForm()
    
    return render(request, 'orders/create_supplier.html', {
        'form': form,
        'title': 'Add Supplier'
    })
    
@login_required
@user_passes_test(is_inventory_or_manager, login_url='users:login')
def update_supplier(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    
    if request.method == 'POST':
        form = SupplierForm(request.POST, instance=supplier)
        if form.is_valid():
            form.save()
            messages.success(request, f"Supplier {supplier.name} updated successfully.")
            return redirect('orders:supplier_list')
    else:
        form = SupplierForm(instance=supplier)
    
    return render(request, 'orders/create_supplier.html', {
        'form': form,
        'supplier': supplier,
        'title': f"Edit Supplier: {supplier.name}",
        'button_label': 'Update Supplier'
    })

@login_required
@user_passes_test(is_manager, login_url='users:login')
def delete_supplier(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    
    # Check if supplier has orders
    orders_count = supplier.orders.count()
    if orders_count > 0:
        messages.error(
            request, 
            f'Cannot delete {supplier.name}. They have {orders_count} associated orders.'
        )
        return redirect('orders:supplier_list')
    
    if request.method == 'POST':
        supplier_name = supplier.name
        supplier.delete()
        messages.success(request, f"Supplier {supplier_name} deleted successfully.")
        return redirect('orders:supplier_list')
    
    return render(request, 'orders/delete_supplier.html', {
        'supplier': supplier,
        'title': f"Delete Supplier: {supplier.name}"
    })