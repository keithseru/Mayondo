from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Q, Sum, Count
from django.core.paginator import Paginator
from django.http import HttpResponse
import csv
from .forms import StockEntryForm
from .models import StockEntry, StockMovement
from products.models import ProductVariant
from orders.models import Order

# Create your views here.
def is_manager(user):
    return user.is_authenticated and user.role == 'MANAGER'

def is_inventory_or_manager(user):
    return user.is_authenticated and user.role in ['INVENORY', 'MANAGER']

# Stock Entry
@login_required
@user_passes_test(is_inventory_or_manager, login_url='login_user')
def stock_entry(request):
    if request.method == 'POST':
        form = StockEntryForm(request.POST)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.entered_by = request.user
            entry.save()
            messages.success(
                request,
                f'Stock entry recorded: {entry.variant}'
                f'{'+' if entry.quantity > 0 else ""}{entry.quantity} units'
            )
            return redirect('inventory:stock_list')
    else:
        form = StockEntryForm()
    
    context = {
        'form':form,
        'title': 'Stock Entry'
    }
    return render(request, 'inventory/stock_entry.html', context)

# Stock List
@login_required
@user_passes_test(is_inventory_or_manager, login_url='login_user')
def stock_list(request):
    entry_type_filter = request.GET.get('entry_type')
    variant_filter = request.GET.get('variant')
    date_from = request.GET.get('date_from')
    export = request.GET.get('export')
    
    entries = StockEntry.objects.select_related('variant__product', 'entered_by')
    
    #Filters
    if entry_type_filter:
        entries = entries.filter(entry_type=entry_type_filter)
    if variant_filter:
        entries = entries.filter(variant__id=variant_filter)
    if date_from:
        entries = entries.filter(entry_date__gte=date_from)
    
    #CSV Export
    if export == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="stock_entries.csv"'
        writer = csv.writer(response)
        writer.writerow(['Date', 'Product', 'Variant', 'Type', 'Quantity', 'Entered By', 'Notes'])
        for entry in entries:
            writer.writerow([
                entry.entry_date.strftime('%Y-%m-%d %H:%M'),
                entry.variant.product.name,
                entry.variant.variant_name,
                entry.get_entry_type_display(),
                entry.quantity,
                entry.entered_by.username if entry.entered_by else 'N/A',
                entry.notes
            ])
        return response
    
    #Pagination
    paginator = Paginator(entries.order_by('-entry_date'), 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get variants for filter
    variants = ProductVariant.objects.filter(is_active=True).select_related('product')
    
    return render(request, 'inventory/stock_list.html', {
        'page_obj': page_obj,
        'variants': variants,
        'entry_type_filter': entry_type_filter,
        'variant_filter': variant_filter,
        'date_from': date_from,
        'title': 'Stock Entries'
    })

# Stock Movements (Audit Trail)
@login_required
@user_passes_test(is_inventory_or_manager, login_url='login_user')
def stock_movements(request):
    movement_type_filter = request.GET.get('movement_type')
    variant_filter = request.GET.get('variant')
    date_from = request.GET.get('date_from')
    
    movements = StockMovement.objects.select_related('variant__product', 'performed_by')
    
    # Filters
    if movement_type_filter:
        movements = movements.filter(movement_type=movement_type_filter)
    if variant_filter:
        movements = movements.filter(variant__id=variant_filter)
    if date_from:
        movements = movements.filter(created_at__gte=date_from)
    
    # Pagination
    paginator = Paginator(movements.order_by('-created_at'), 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get variants for filter
    variants = ProductVariant.objects.filter(is_active=True).select_related('product')
    
    return render(request, 'inventory/stock_movements.html', {
        'page_obj': page_obj,
        'variants': variants,
        'movement_type_filter': movement_type_filter,
        'variant_filter': variant_filter,
        'date_from': date_from,
        'title': 'Stock Movements'
    })

# Dashboard
@login_required
@user_passes_test(is_inventory_or_manager, login_url='login_user')
def inventory_dashboard(request):
    # Low stock items (below reorder level)
    low_stock_items = ProductVariant.objects.filter(
        is_active=True,
        stock_quantity__lte=10
    ).select_related('product').order_by('stock_quantity')[:10]
    
    # Out of stock items
    out_of_stock = ProductVariant.objects.filter(
        is_active=True,
        stock_quantity=0
    ).count()
    
    # Total variants and stock value
    total_variants = ProductVariant.objects.filter(is_active=True).count()
    
    # Calculate total stock value
    variants = ProductVariant.objects.filter(is_active=True)
    total_stock_value = sum(v.stock_quantity * v.price for v in variants)
    
    # Pending orders
    pending_orders = Order.objects.filter(status='PENDING').count()
    
    # Recent stock entries
    recent_entries = StockEntry.objects.select_related(
        'variant__product', 'entered_by'
    ).order_by('-entry_date')[:10]
    
    context = {
        'low_stock_items': low_stock_items,
        'low_stock_count': low_stock_items.count(),
        'out_of_stock': out_of_stock,
        'total_variants': total_variants,
        'total_stock_value': total_stock_value,
        'pending_orders': pending_orders,
        'recent_entries': recent_entries,
        'title': 'Inventory Dashboard'
    }
    
    return render(request, 'inventory/dashboard.html', context)

# Reports
@login_required
@user_passes_test(is_inventory_or_manager, login_url='login_user')
def inventory_reports(request):
    # Low stock items
    low_stock_threshold = int(request.GET.get('threshold', 10))
    low_stock_items = ProductVariant.objects.filter(
        is_active=True,
        stock_quantity__lte=low_stock_threshold
    ).select_related('product', 'product__category').order_by('stock_quantity')
    
    # Out of stock items
    out_of_stock_items = ProductVariant.objects.filter(
        is_active=True,
        stock_quantity=0
    ).select_related('product')
    
    # Total inventory value
    all_variants = ProductVariant.objects.filter(is_active=True)
    total_stock_value = sum(v.stock_quantity * v.price for v in all_variants)
    total_items = sum(v.stock_quantity for v in all_variants)
    
    # Stock by category
    from products.models import Category
    categories = Category.objects.filter(is_active=True)
    category_stock = []
    for category in categories:
        variants = ProductVariant.objects.filter(
            product__category=category,
            is_active=True
        )
        total = sum(v.stock_quantity for v in variants)
        value = sum(v.stock_quantity * v.price for v in variants)
        category_stock.append({
            'category': category,
            'total_items': total,
            'total_value': value,
            'variant_count': variants.count()
        })
    
    # Pending deliveries
    pending_orders = Order.objects.filter(
        status__in=['PENDING', 'PARTIAL']
    ).count()
    
    context = {
        'low_stock_items': low_stock_items,
        'low_stock_threshold': low_stock_threshold,
        'out_of_stock_items': out_of_stock_items,
        'total_stock_value': total_stock_value,
        'total_items': total_items,
        'category_stock': category_stock,
        'pending_orders': pending_orders,
        'title': 'Inventory Reports'
    }
    
    return render(request, 'inventory/reports.html', context)