from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta, datetime
from sales.models import Sale, Customer
from orders.models import Order
from products.models import ProductVariant
from users.models import Employee
from inventory.models import StockMovement

# Create your views here.

def is_manager(user):
    return user.is_authenticated and user.role == 'MANAGER'

@login_required
@user_passes_test(is_manager, login_url='login_user')
def manager_dashboard(request):
    """Main manager dashboard with overview of all operations"""
    
    # Date ranges
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    # Sales Statistics
    total_sales = Sale.objects.filter(status='COMPLETED').count()
    today_sales = Sale.objects.filter(
        sale_date__date=today,
        status='COMPLETED'
    )
    week_sales = Sale.objects.filter(
        sale_date__date__gte=week_ago,
        status='COMPLETED'
    )
    month_sales = Sale.objects.filter(
        sale_date__date__gte=month_ago,
        status='COMPLETED'
    )
    pending_sales = Sale.objects.filter(status='PENDING').count()
    
    # Revenue calculations
    today_revenue = sum(sale.total for sale in today_sales)
    week_revenue = sum(sale.total for sale in week_sales)
    month_revenue = sum(sale.total for sale in month_sales)
    
    # Orders Statistics
    total_orders = Order.objects.count()
    pending_orders = Order.objects.filter(status='PENDING').count()
    partial_orders = Order.objects.filter(status='PARTIAL').count()
    
    # Inventory Statistics
    total_products = ProductVariant.objects.filter(is_active=True).count()
    low_stock_items = ProductVariant.objects.filter(
        is_active=True,
        stock_quantity__lte=10
    ).count()
    out_of_stock = ProductVariant.objects.filter(
        is_active=True,
        stock_quantity=0
    ).count()
    
    # Calculate total inventory value
    variants = ProductVariant.objects.filter(is_active=True)
    inventory_value = sum(v.stock_quantity * v.price for v in variants)
    
    # Staff Statistics
    staff_count = Employee.objects.filter(
        role__in=['SALES', 'INVENTORY', 'MANAGER'],
        is_active=True
    ).count()
    
    # Recent Activities
    recent_sales = Sale.objects.select_related('customer', 'created_by').order_by('-sale_date')[:5]
    recent_orders = Order.objects.select_related('supplier', 'created_by').order_by('-order_date')[:5]
    
    # Top selling products this month
    top_products = ProductVariant.objects.filter(
        sale_items__sale__status='COMPLETED',
        sale_items__sale__sale_date__date__gte=month_ago
    ).annotate(
        total_sold=Sum('sale_items__quantity')
    ).order_by('-total_sold')[:5]
    
    # Top customers this month
    top_customers = Customer.objects.filter(
        sales__status='COMPLETED',
        sales__sale_date__date__gte=month_ago
    ).annotate(
        total_spent=Sum('sales__items__unit_price')
    ).order_by('-total_spent')[:5]
    
    context = {
        # Sales
        'total_sales': total_sales,
        'today_sales': today_sales.count(),
        'week_sales': week_sales.count(),
        'month_sales': month_sales.count(),
        'pending_sales': pending_sales,
        'today_revenue': today_revenue,
        'week_revenue': week_revenue,
        'month_revenue': month_revenue,
        
        # Orders
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'partial_orders': partial_orders,
        
        # Inventory
        'total_products': total_products,
        'low_stock_items': low_stock_items,
        'out_of_stock': out_of_stock,
        'inventory_value': inventory_value,
        
        # Staff
        'staff_count': staff_count,
        
        # Recent activities
        'recent_sales': recent_sales,
        'recent_orders': recent_orders,
        'top_products': top_products,
        'top_customers': top_customers,
        
        'title': 'Manager Dashboard'
    }
    
    return render(request, 'manager/dashboard.html', context)

@login_required
@user_passes_test(is_manager, login_url='login_user')
def manager_reports(request):
    """Comprehensive reports for manager"""
    
    # Date range filters
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if not date_from:
        date_from = timezone.now().replace(day=1).date()
    else:
        date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
    
    if not date_to:
        date_to = timezone.now().date()
    else:
        date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
    
    # Sales Report
    sales = Sale.objects.filter(
        sale_date__date__gte=date_from,
        sale_date__date__lte=date_to,
        status='COMPLETED'
    )
    total_sales = sales.count()
    total_revenue = sum(sale.total for sale in sales)
    average_sale = total_revenue / total_sales if total_sales > 0 else 0
    
    # Orders Report
    orders = Order.objects.filter(
        order_date__date__gte=date_from,
        order_date__date__lte=date_to
    )
    total_orders = orders.count()
    total_order_value = sum(order.total_amount for order in orders)
    
    # Inventory Report
    total_variants = ProductVariant.objects.filter(is_active=True).count()
    low_stock = ProductVariant.objects.filter(
        is_active=True,
        stock_quantity__lte=10
    ).count()
    
    # Staff Performance
    staff_performance = Employee.objects.filter(
        role__in=['SALES', 'INVENTORY', 'MANAGER'],
        is_active=True
    ).annotate(
        sales_created=Count('sales_created', filter=Q(
            sales_created__sale_date__date__gte=date_from,
            sales_created__sale_date__date__lte=date_to
        )),
        orders_created=Count('created_orders', filter=Q(
            created_orders__order_date__date__gte=date_from,
            created_orders__order_date__date__lte=date_to
        ))
    ).order_by('-sales_created')
    
    # Customer Report
    total_customers = Customer.objects.filter(is_active=True).count()
    new_customers = Customer.objects.filter(
        created_at__date__gte=date_from,
        created_at__date__lte=date_to
    ).count()
    
    # Stock movements
    stock_in = StockMovement.objects.filter(
        created_at__date__gte=date_from,
        created_at__date__lte=date_to,
        quantity__gt=0
    ).aggregate(total=Sum('quantity'))['total'] or 0
    
    stock_out = StockMovement.objects.filter(
        created_at__date__gte=date_from,
        created_at__date__lte=date_to,
        quantity__lt=0
    ).aggregate(total=Sum('quantity'))['total'] or 0
    
    context = {
        'date_from': date_from,
        'date_to': date_to,
        
        # Sales
        'total_sales': total_sales,
        'total_revenue': total_revenue,
        'average_sale': average_sale,
        
        # Orders
        'total_orders': total_orders,
        'total_order_value': total_order_value,
        
        # Inventory
        'total_variants': total_variants,
        'low_stock': low_stock,
        'stock_in': stock_in,
        'stock_out': abs(stock_out),
        
        # Staff
        'staff_performance': staff_performance,
        
        # Customers
        'total_customers': total_customers,
        'new_customers': new_customers,
        
        'title': 'Manager Reports'
    }
    
    return render(request, 'manager/reports.html', context)
