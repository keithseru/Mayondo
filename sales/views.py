from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Sum, Count, Q
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.utils.timezone import now
from django.db import transaction
from utils.pdf_generator import SalesReportPDF
from utils.excel_generator import SalesReportExcel
import io
import csv
from datetime import datetime, timezone
from .models import Sale, Customer, SaleItem
from .forms import SaleForm, CustomerForm, SaleItemFormSet

# Create your views here.
# Roles
def is_manager(user):
    return user.is_authenticated and user.role == 'MANAGER'

def is_sales_or_manager(user):
    return user.is_authenticated and user.role in ['SALES', 'MANAGER']

# SALES VIEW

# List of sales
@login_required
@user_passes_test(is_sales_or_manager, login_url='users:login')
def sale_list(request):
    status_filter = request.GET.get('status')
    customer_filter = request.GET.get('customer')
    staff_filter = request.GET.get('staff')
    product_filter = request.GET.get('product')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    export = request.GET.get('export')
    
    sales = Sale.objects.select_related('customer', 'created_by').prefetch_related('items__product_variant')
    
    # Filters
    if status_filter:
        sales = sales.filter(status=status_filter)
    if customer_filter:
        sales = sales.filter(customer__id=customer_filter)
    if staff_filter:
        sales = sales.filter(created_by__id=staff_filter)
    if product_filter:
        sales = sales.filter(items__product_variant__id=product_filter)
    if date_from:
        sales = sales.filter(sale_date__gte=date_from)
    if date_to:
        sales = sales.filter(sale_date__lte=date_to)
        
    # CSV Export
    if export == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="sales.csv"'
        writer = csv.writer(response)
        writer.writerow(['Sale ID', 'Customer', 'Date', 'Status', 'Payment', 'Items', 'Subtotal', 'Delivery Fee', 'Total'])
        
        for sale in sales:
            writer.writerow([
                sale.id,
                sale.customer.full_name,
                sale.sale_date.strftime('%Y-%m-%d %H:%M'),
                sale.get_status_display(),
                sale.get_payment_method_display(),
                sale.item_count,
                sale.subtotal,
                sale.total,
            ])
        return response
    
    # Pagination
    paginator = Paginator(sales.order_by('-sale_date'), 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get customers fro filter dropdown
    customers = Customer.objects.filter(is_active=True).order_by('last_name', 'first_name')
    
    context = {
        'page_obj': page_obj,
        'customers': customers,
        'status_filter': status_filter,
        'customer_filter': customer_filter,
        'date_from': date_from,
        'date_to': date_to,
        'title': 'Sales List',
    }
    
    return render(request, 'sales/sales_list.html', context)

# Create new sale
@login_required
@user_passes_test(is_sales_or_manager, login_url='users:login')
def create_sale(request):
    if request.method == 'POST':
        form = SaleForm(request.POST)
        formset = SaleItemFormSet(request.POST)
        
        if form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic():
                    # Save sale
                    sale = form.save(commit=False)
                    sale.created_by = request.user
                    sale.status = 'PENDING'
                    sale.save()
                    
                    # Save formset with the sale instance
                    formset.instance = sale
                    items = formset.save(commit=False)
                    
                    # Filter out empty forms (forms without product_variant)
                    valid_items = [item for item in items if hasattr(item, 'product_variant_id') and item.product_variant_id]
                    
                    # Check if at least one item exists
                    if not valid_items:
                        raise ValidationError('At least one sale item is required.')
                    
                    # Process each valid item
                    for item in valid_items:
                        # Validate stock
                        if item.quantity > item.product_variant.stock_quantity:
                            raise ValidationError(
                                f'Insufficient stock for {item.product_variant}. '
                                f'Available: {item.product_variant.stock_quantity}, '
                                f'Requested: {item.quantity}'
                            )
                        item.save()
                    
                    # Delete any items marked for deletion
                    for item in formset.deleted_objects:
                        item.delete()
                    
                    # Update delivery fee if needed
                    if sale.delivery_required:
                        sale.update_delivery_fee()
                        
                    messages.success(
                        request, f"Sale #{sale.id} created successfully. Total: UGX {sale.total:,}"
                    )
                    return redirect('sales:sale_detail', pk=sale.pk)
            except ValidationError as e:
                messages.error(request, str(e))
        else:
            # Show specific formset errors for debugging
            if formset.errors:
                for i, form_errors in enumerate(formset.errors):
                    if form_errors:
                        messages.error(request, f'Item {i+1}: {form_errors}')
            messages.error(request, 'Please correct the errors below')
    else:
        form = SaleForm()
        formset = SaleItemFormSet()
    
    context = {
        'form': form,
        'formset': formset,
        'title': 'Record New Sale',
    }
    
    return render(request, 'sales/create_sale.html', context)

# Details of a sale
@login_required
@user_passes_test(is_sales_or_manager, login_url='users:login')
def sale_detail(request, pk):
    sale = get_object_or_404(
        Sale.objects.select_related('customer', 'created_by').prefetch_related('items__product_variant__product'), pk=pk
    )
    return render(request, 'sales/sale_detail.html', {'sale': sale, 'title': f'Sale #{sale.id} Details'})

# Complete sale confirmation
@login_required
@user_passes_test(is_sales_or_manager, login_url='users:login')
def complete_sale(request, pk):
    '''Complete a sale and update inventory'''
    sale = get_object_or_404(Sale, pk=pk)
    
    if sale.status == 'COMPLETED':
        messages.warning(request, 'This sale is already completed')
        return redirect('sales:sale_detail', pk=pk)
    
    if request.method == 'POST':
        try:
            sale.complete_sale()
            messages.success(
                request,
                f'Sale #{sale.id} completed successfully! Stock has been updated.'
            )
        except ValidationError as e:
            messages.error(request, str(e))
        return redirect('sales:sale_detail', pk=pk)
    
    context = {
        'sale': sale,
        'title': f"Complete Sale #{sale.id}"
    }
    
    return render(request, 'sales/confirm_complete.html', context)

# Cancel sale
@login_required
@user_passes_test(is_manager, login_url='users:login')
def cancel_sale(request, pk):
    '''Cancel a sale and restore inventory if it ws completed'''
    sale = get_object_or_404(Sale, pk=pk)
    
    if sale.status == 'CANCELLED':
        messages.warning(request, 'This sale is already cancelled.')
        return redirect('sales:sale_detail', pk=pk)
    
    if request.method == "POST":
        try:
            sale.cancel_sale()
            messages.success(
                request,
                f'Sale #{sale.id} cancelled successfully. Stock has been restored if applicable.'
            )
        except ValidationError as e:
            messages.error(request, str(e))
        return redirect('sales:sale_detail', pk=pk)
    context = {
        'sale': sale,
        'title': f'Cancel Sale #{sale.id}'
    }
    
    return render(request, 'sales/confirm_cancel.html', context)

# Delete a sale
@login_required
@user_passes_test(is_manager, login_url='users:login')
def delete_sale(request, pk):
    sale = get_object_or_404(Sale, pk=pk)
    
    if sale.status == 'COMPLETED':
        messages.error(request, 'Cannot delete completed sales. Cancel first, then delete.')
        return redirect('sales:sale_detail', pk=pk)
    
    if request.method == 'POST':
        sale_id = sale.id
        sale.delete()
        messages.success(request, f"Sale #{sale_id} deleted successfully.")
        return redirect('sales:sale_list')
    
    context = {
        'sale': sale,
        'title': f"Delete Sale #{sale.id}"
    }
    

# CUSTOMER MANAGEMENT VIEWS
@login_required
@user_passes_test(is_sales_or_manager, login_url='users:login')
def customer_list(request):
    search = request.GET.get('search', '')
    
    customers = Customer.objects.filter(is_active=True)
    
    if search:
        customers = customers.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(phone__icontains=search) |
            Q(email__icontains=search)
        )
    
    # Add the number of completed sale to each customer
    customers = customers.annotate(
        total_sales=Count('sales', filter=Q(sales__status='COMPLETED'))
    ).order_by('last_name', 'first_name')
    
    # Add the pagnation
    paginator = Paginator(customers, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'search': search,
        'page_obj': page_obj,
        'title': 'Customer List',
    }
    return render(request, 'sales/customer_list.html', context)
    
# Create a new customer
@login_required
@user_passes_test(is_sales_or_manager, login_url='users:login')
def create_customer(request):
    if request.method == 'POST':
        form = CustomerForm(request.POST)
        if form.is_valid():
            customer = form.save()
            messages.success(request, f"Customer {customer.full_name} added successfully.")
            
            # Check if this was called from sale creation
            if request.GET.get('next') == 'sale':
                return redirect('sales:create_sale')
            return redirect('sales:customer_list')
    else:
        form = CustomerForm()
    context = {
        'form': form,
        'title': 'Add Customer'
    }
    
    return render(request, 'sales/create_customer.html', context)

# Update customer details
@login_required
@user_passes_test(is_sales_or_manager, login_url='users:login')
def update_customer(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    
    if request.method == 'POST':
        form = CustomerForm(request.POST, instance=customer)
        if form.is_valid():
            form.save()
            messages.success(request, f"Customer {customer.full_name} updated successfully.")
            return redirect('sales:customer_list')
    else:
        form = CustomerForm(instance=customer)
        
    context = {
        'form':form,
        'customer':customer,
        'title': f"Edit Customer: {customer.full_name}",
        'button_label': 'Update Customer'
    }
    
    return render(request, 'create_customer.html', context)

# Delete a customer
@login_required
@user_passes_test(is_manager, login_url='users:login')
def delete_customer(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    
    # Check if customer has sales
    sales_count = customer.sales.count()
    if sales_count > 0:
        messages.error(
            request,
            f'Cannot delete {customer.full_name}. They have {sales_count} associated sales.'
        )
        return redirect('sales:customer_list')
    
    if request.method == 'POST':
        customer_name = customer.full_name
        customer.delete()
        messages.success(request, f"Customer {customer_name} deleted successfully.")
        return redirect('sales:customer_list')
    
    context = {
        'customer': customer,
        'title': f'Delete {customer.full_name}'
    }
    return render(request, 'sales/delete_customer.html', context)

# Sales Dashboard
@login_required
@user_passes_test(is_sales_or_manager, login_url='users:login')
def sales_dashboard(request):
    # COMPLETED SALES ONLY
    #Today's stats
    today = now().date()
    today_sales = Sale.objects.filter(
        sale_date__date = today,
        status = 'COMPLETED'
    )
    
    # This month's stats
    month_start = today.replace(day=1)
    month_sales = Sale.objects.filter(
        sale_date__gte=month_start,
        status='COMPLETED'
    )
    
    #Pending Sales
    pending_sales = Sale.objects.filter(status='PENDING').count() 
    
    # Recent sales
    recent_sales = Sale.objects.select_related('customer', 'created_by')[:10]
    
    context = {
        'today_sales_count': today_sales.count(),
        'today_revenue': sum(sale.total for sale in today_sales),
        'month_sales_count': month_sales.count(),
        'month_revenue': sum(sale.total for sale in month_sales),
        'pending_sales': pending_sales,
        'recent_sales': recent_sales,
        'title': 'Sales Dashboard'
    }
    
    return render(request, 'sales/dashboard.html', context)

# Reports
@login_required
@user_passes_test(is_sales_or_manager, login_url='users:login')
def sales_reports(request):
    #Date range
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    # Default to current month
    if not date_from:
        date_from = now().replace(day=1).date()
    else:
        date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
    
    if not date_to:
        date_to = now().date()
    else:
        date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
    
    # Sales in range
    sales = Sale.objects.filter(
        sale_date__date__gte=date_from,
        sale_date__date__lte=date_to,
        status='COMPLETED'
    )
    
    total_revenue = sum(sale.total for sale in sales)
    total_sales = sales.count()
    
    # Top customers
    top_customers = Customer.objects.filter(
        sales__status='COMPLETED',
        sales__sale_date__date__gte=date_from,
        sales__sale_date__date__lte=date_to
    ).annotate(
        total_spent=Sum('sales__items__unit_price')
    ).order_by('-total_spent')[:10]
    
    # Top products
    from products.models import ProductVariant
    top_products = ProductVariant.objects.filter(
        sale_items__sale__status='COMPLETED',
        sale_items__sale__sale_date__date__gte=date_from,
        sale_items__sale__sale_date__date__lte=date_to
    ).annotate(
        total_sold=Sum('sale_items__quantity'),
        revenue=Sum('sale_items__unit_price')
    ).order_by('-total_sold')[:10]
    
    # Daily sales (for chart)
    from django.db.models.functions import TruncDate
    daily_sales = sales.annotate(
        date=TruncDate('sale_date')
    ).values('date').annotate(
        count=Count('id'),
        revenue=Sum('items__unit_price')
    ).order_by('date')
    
    context = {
        'date_from': date_from,
        'date_to': date_to,
        'total_revenue': total_revenue,
        'total_sales': total_sales,
        'average_sale': total_revenue / total_sales if total_sales > 0 else 0,
        'top_customers': top_customers,
        'top_products': top_products,
        'daily_sales': daily_sales,
        'title': 'Sales Reports'
    }
    
    return render(request, 'sales/reports.html', context)

@login_required
@user_passes_test(is_sales_or_manager, login_url='users:login')
def export_sales_report(request):
    '''Export sales report as PDF or Excel'''
    export_format = request.GET.get('format', 'pdf')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date__to')
    
    # Date reange filters 
    if not date_from:
        date_from = timezone().now.replace(day=1).date()
    else:
        date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
    
    if not date_to:
        date_to = timezone().now()
    else:
        date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
        
    # Get sales daa
    sales = Sale.objects.filter(
        sale_date__date__gte=date_from,
        sale_date__date__lte=date_to,
        status='COMPLETED'
    ).select_related('customer')
    
    # Prepare data 
    sales_data = []
    for sale in sales:
        sales_data.apped({
            'date': sale.sale_date,
            'customer': sale.customer.full_name,
            'items':sale.item_count,
            'amount':sale.total,
            'status':sale.get_status_display()
        })
        
    #Calculate summary
    total_sales = sales.count()
    total_revenue = sum(sale.total for sale in sales)
    average_sale = total_revenue / total_sales if total_sales > 0 else 0
    total_customers = Customer.objects.filter(sales__in=sales).distinct().count()
    
    summary = {
        'total_sales': total_sales,
        'total_revenue': total_revenue,
        'average_sale': average_sale,
        'total_customers': total_customers,
    }

    # Generate report
    if export_format == 'pdf':
        # Generate PDF
        buffer = io.BytesIO()
        pdf_generator = SalesReportPDF(date_from, date_to, sales_data, summary)
        pdf_generator.build()
        pdf_generator.generate(buffer)
        buffer.seek(0)
        
        response = HttpResponse(buffer.read(), content_type='application/pdf')
        filename = f'sales_report_{date_from}_{date_to}'.pdf
        response['Content-Disposition'] = f'attachament; filename="{filename}"'
    
    elif export_format == 'excel':
        # Generate Excel
        buffer = io.BytesIO()
        excel_generator = SalesReportExcel(date_from, date_to, sales_data, summary)
        excel_generator.build()
        excel_generator.save(buffer)
        buffer.seek(0)
        
        response = HttpResponse(buffer.read, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        filename = f'sales_report_{date_from}_{date_to}'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    else:
        return HttpResponse('Invalif format', status=400)
    
    return response
