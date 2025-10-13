from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Q, Sum, Count
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.utils import timezone
from utils.excel_generator import InventoryReportExcel
from utils.pdf_generator import InventoryReportPDF
import io
import csv
from .forms import StockEntryForm
from .models import StockEntry, StockMovement
from products.models import ProductVariant, Category
from orders.models import Order

# Create your views here.
def is_manager(user):
    return user.is_authenticated and user.role == 'MANAGER'

def is_inventory_or_manager(user):
    return user.is_authenticated and user.role in ['INVENTORY', 'MANAGER']

# Stock Entry
@login_required
@user_passes_test(is_inventory_or_manager, login_url='users:login')
def stock_entry(request):
    if request.method == 'POST':
        form = StockEntryForm(request.POST)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.entered_by = request.user

            # Get the quantity and entry type
            qty = entry.quantity
            entry_type = entry.entry_type

            # Normalize quantity based on entry type
            # DAMAGE should always reduce stock (negative)
            if entry_type == 'DAMAGE':
                qty = -abs(qty)  # Force negative
            # ADDITION and RETURN should always add stock (positive)
            elif entry_type in ['ADDITION', 'RETURN']:
                qty = abs(qty)   # Force positive
            # ADJUSTMENT and CORRECTION can be either positive or negative
            # User's input is respected

            # Validate stock won't go negative
            variant = entry.variant
            new_stock = variant.stock_quantity + qty
            
            if new_stock < 0:
                messages.error(
                    request,
                    f'Cannot process entry. Stock would become negative ({new_stock}). '
                    f'Current stock: {variant.stock_quantity}'
                )
                return redirect('inventory:stock_entry')

            # Update stock
            variant.stock_quantity = new_stock
            variant.save()

            # Save entry with normalized quantity
            entry.quantity = qty
            entry.save()

            # Feedback message
            action = "added to" if qty > 0 else "deducted from"
            messages.success(
                request,
                f'Stock entry recorded: {abs(qty)} units {action} {entry.variant}'
            )
            return redirect('inventory:stock_list')
    else:
        form = StockEntryForm()

    context = {
        'form': form,
        'title': 'Stock Entry'
    }
    return render(request, 'inventory/stock_entry.html', context)


# Stock List
@login_required
@user_passes_test(is_inventory_or_manager, login_url='users:login')
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
@user_passes_test(is_inventory_or_manager, login_url='users:login')
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
@user_passes_test(is_inventory_or_manager, login_url='users:login')
def inventory_dashboard(request):
    # Centralized active variants queryset
    active_variants = ProductVariant.objects.filter(is_active=True)

    # Low stock items
    low_stock_items = active_variants.filter(stock_quantity__lte=10).select_related('product').order_by('stock_quantity')[:10]

    # Out of stock count
    out_of_stock = active_variants.filter(stock_quantity=0).count()

    # Total variants and stock value
    total_variants = active_variants.count()
    total_stock_value = sum(v.stock_quantity * v.price for v in active_variants)

    # Pending orders
    PENDING_STATUSES = ['PENDING', 'PARTIAL']
    pending_orders_qs = Order.objects.filter(status__in=PENDING_STATUSES)
    pending_orders_list = pending_orders_qs.select_related('supplier', 'created_by').order_by('-order_date')[:5]
    pending_orders_count = pending_orders_qs.count()

    # Recent stock entries
    recent_entries = StockEntry.objects.select_related('variant__product', 'entered_by').order_by('-entry_date')[:10]

    context = {
        'low_stock_items': low_stock_items,
        'low_stock_count': low_stock_items.count(),
        'out_of_stock': out_of_stock,
        'total_variants': total_variants,
        'total_stock_value': total_stock_value,
        'pending_orders': pending_orders_count,
        'pending_orders_list': pending_orders_list,
        'recent_entries': recent_entries,
        'title': 'Inventory Dashboard',
        'onboarding_hints': {
            'pending_orders': "These orders are awaiting delivery confirmation. Click 'Confirm Delivery' once items arrive."
        }
    }

    return render(request, 'inventory/dashboard.html', context)


# Reports
@login_required
@user_passes_test(is_inventory_or_manager, login_url='users:login')
def inventory_reports(request):
    # Threshold for low stock (default: 10)
    low_stock_threshold = int(request.GET.get('threshold', 10))

    # Active variants
    active_variants = ProductVariant.objects.filter(is_active=True)

    # Low stock items
    low_stock_items = active_variants.filter(
        stock_quantity__lte=low_stock_threshold
    ).select_related('product', 'product__category').order_by('stock_quantity')

    # Out of stock items
    out_of_stock_items = active_variants.filter(
        stock_quantity=0
    ).select_related('product')

    # Total inventory value and item count
    total_stock_value = sum(v.stock_quantity * v.price for v in active_variants)
    total_items = sum(v.stock_quantity for v in active_variants)

    # Stock by category
    categories = Category.objects.filter(is_active=True)
    category_stock = []
    for category in categories:
        variants = active_variants.filter(product__category=category)
        total = sum(v.stock_quantity for v in variants)
        value = sum(v.stock_quantity * v.price for v in variants)
        category_stock.append({
            'category': category,
            'total_items': total,
            'total_value': value,
            'variant_count': variants.count()
        })

    # Pending deliveries
    PENDING_STATUSES = ['PENDING', 'PARTIAL']
    pending_orders_qs = Order.objects.filter(status__in=PENDING_STATUSES)
    pending_orders_list = pending_orders_qs.select_related('supplier', 'created_by').order_by('-order_date')[:10]
    pending_orders_count = pending_orders_qs.count()

    context = {
        'low_stock_items': low_stock_items,
        'low_stock_threshold': low_stock_threshold,
        'out_of_stock_items': out_of_stock_items,
        'total_stock_value': total_stock_value,
        'total_items': total_items,
        'category_stock': category_stock,
        'pending_orders': pending_orders_count,
        'pending_orders_list': pending_orders_list,
        'title': 'Inventory Reports',
        'onboarding_hints': {
            'pending_orders': "These orders are awaiting delivery confirmation. Use the action button once items arrive."
        }
    }

    return render(request, 'inventory/reports.html', context)

@login_required
@user_passes_test(is_inventory_or_manager, login_url='users:login')
def export_inventory_report(request):
    """Export inventory report as PDF or Excel"""
    export_format = request.GET.get('format', 'pdf')
    display = request.GET.get('display', 'download')
    
    # Get inventory data - ALL active variants
    active_variants = ProductVariant.objects.filter(is_active=True).select_related('product', 'product__category')
    
    # Low stock items
    low_stock_threshold = int(request.GET.get('threshold', 10))
    low_stock_items = active_variants.filter(
        stock_quantity__lte=low_stock_threshold
    )
    
    # Out of stock items
    out_of_stock_items = active_variants.filter(stock_quantity=0)
    
    # Prepare data for low stock items (for the detailed table)
    inventory_data = {
        'low_stock': []
    }
    
    for item in low_stock_items:
        inventory_data['low_stock'].append({
            'product': item.product.name,
            'variant': item.variant_name,
            'stock': item.stock_quantity,
            'reorder_level': item.reorder_level,
        })
    
    # Calculate summary - Count ALL active variants
    total_products = active_variants.count()  # This should be 621
    low_stock_count = low_stock_items.count()  # Items below threshold
    out_of_stock_count = out_of_stock_items.count()  # Items with 0 stock
    total_value = sum(v.stock_quantity * v.price for v in active_variants)
    
    # Debug: Print to console to verify counts
    print(f"DEBUG - Total Products: {total_products}")
    print(f"DEBUG - Low Stock: {low_stock_count}")
    print(f"DEBUG - Out of Stock: {out_of_stock_count}")
    print(f"DEBUG - Total Value: {total_value}")
    
    summary = {
        'total_products': total_products,  # Should show 621
        'low_stock': low_stock_count,
        'out_of_stock': out_of_stock_count,
        'total_value': total_value,
    }
    
    # Generate report
    if export_format == 'pdf':
        # Generate PDF
        buffer = io.BytesIO()
        pdf_generator = InventoryReportPDF(inventory_data, summary)
        pdf_generator.build()
        pdf_generator.generate(buffer)
        buffer.seek(0)
        
        response = HttpResponse(buffer.read(), content_type='application/pdf')
        filename = f'inventory_report_{timezone.now().strftime("%Y%m%d")}.pdf'
       
        if display == 'inline':
            response['Content-Disposition'] = f'inline; filename="{filename}"'
        else:
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
    elif export_format == 'excel':
        # Generate Excel
        buffer = io.BytesIO()
        excel_generator = InventoryReportExcel(inventory_data, summary)
        excel_generator.build()
        excel_generator.save(buffer)
        buffer.seek(0)
        
        response = HttpResponse(
            buffer.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        filename = f'inventory_report_{timezone.now().strftime("%Y%m%d")}.xlsx'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    else:
        return HttpResponse("Invalid format", status=400)
    
    return response
@login_required
@user_passes_test(is_inventory_or_manager, login_url='users:login')
def export_inventory_report(request):
    """Export inventory report as PDF or Excel"""
    export_format = request.GET.get('format', 'pdf')
    
    # Get inventory data
    active_variants = ProductVariant.objects.filter(is_active=True)
    
    # Low stock items (threshold: 10 or custom)
    low_stock_threshold = int(request.GET.get('threshold', 10))
    low_stock_items = active_variants.filter(
        stock_quantity__lte=low_stock_threshold
    ).select_related('product', 'product__category')
    
    # Out of stock items
    out_of_stock_items = active_variants.filter(stock_quantity=0)
    
    # Prepare data for low stock items
    inventory_data = {
        'low_stock': []
    }
    
    for item in low_stock_items:
        inventory_data['low_stock'].append({
            'product': item.product.name,
            'variant': item.variant_name,
            'stock': item.stock_quantity,
            'reorder_level': item.reorder_level,
        })
    
    # Calculate summary - FIXED: now counts ALL active products
    total_products = active_variants.count()  # All active variants
    low_stock = low_stock_items.count()
    out_of_stock = out_of_stock_items.count()
    total_value = sum(v.stock_quantity * v.price for v in active_variants)
    
    summary = {
        'total_products': total_products,  # Now shows correct total
        'low_stock': low_stock,
        'out_of_stock': out_of_stock,
        'total_value': total_value,
    }
    
    # Generate report
    if export_format == 'pdf':
        # Generate PDF
        buffer = io.BytesIO()
        pdf_generator = InventoryReportPDF(inventory_data, summary)
        pdf_generator.build()
        pdf_generator.generate(buffer)
        buffer.seek(0)
        
        response = HttpResponse(buffer.read(), content_type='application/pdf')
        filename = f'inventory_report_{timezone.now().strftime("%Y%m%d")}.pdf'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
    elif export_format == 'excel':
        # Generate Excel
        buffer = io.BytesIO()
        excel_generator = InventoryReportExcel(inventory_data, summary)
        excel_generator.build()
        excel_generator.save(buffer)
        buffer.seek(0)
        
        response = HttpResponse(
            buffer.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        filename = f'inventory_report_{timezone.now().strftime("%Y%m%d")}.xlsx'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    else:
        return HttpResponse("Invalid format", status=400)
    
    return response
