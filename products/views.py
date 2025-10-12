from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import HttpResponse
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.db import transaction
import csv
from .models import Product, Category, Unit, ProductVariant
from .forms import ProductForm, ProductVariantFormSet, UnitForm, CategoryForm

# Create your views here.

def is_manager(user):
    return user.is_authenticated and user.role == 'MANAGER'

# Product Views - Viewable by all authenticated users
@login_required
def product_list(request):
    category_filter = request.GET.get("category")
    unit_filter = request.GET.get("unit")
    stock_filter = request.GET.get("stock")
    search = request.GET.get("search")
    export = request.GET.get("export")
    sort = request.GET.get("sort", "name")
    order = request.GET.get("order", "asc")

    # Base queryset
    products = Product.objects.filter(is_active=True).select_related('category', 'unit', 'supplier')

    # Search
    if search:
        products = products.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search) |
            Q(category__name__icontains=search)
        )

    # Filtering
    if category_filter:
        products = products.filter(category_id=category_filter)
    if unit_filter:
        products = products.filter(unit_id=unit_filter)
    if stock_filter == "low":
        products = products.filter(variants__stock_quantity__lte=10, variants__is_active=True).distinct()
    elif stock_filter == "out":
        products = products.filter(variants__stock_quantity=0, variants__is_active=True).distinct()

    # Sorting
    order_toggle = "desc" if order == "asc" else "asc"
    sort_field = f"{'' if order == 'asc' else '-'}{sort}"
    products = products.order_by(sort_field)

    # CSV export
    if export == "csv":
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = "attachment; filename=products.csv"
        writer = csv.writer(response)
        writer.writerow(["Product", "Category", "Unit", "Supplier", "Variant", "Price (UGX)", "Stock"])
        for product in products:
            for variant in product.variants.filter(is_active=True):
                writer.writerow([
                    product.name,
                    product.category.name,
                    product.unit.name,
                    product.supplier.name if product.supplier else 'N/A',
                    variant.variant_name,
                    variant.price,
                    variant.stock_quantity
                ])
        return response

    # Pagination
    paginator = Paginator(products, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Get categories and units for filters
    categories = Category.objects.filter(is_active=True).order_by('name')
    units = Unit.objects.filter(is_active=True).order_by('name')

    context = {
        "page_obj": page_obj,
        "categories": categories,
        "units": units,
        "category_filter": category_filter,
        "unit_filter": unit_filter,
        "stock_filter": stock_filter,
        "search": search,
        "sort": sort,
        "order": order,
        "order_toggle": order_toggle,
        "title": "Products"
    }

    return render(request, "products/product_list.html", context)

@login_required
def product_detail(request, pk):
    product = get_object_or_404(
        Product.objects.select_related('category', 'unit', 'supplier')
        .prefetch_related('variants'),
        pk=pk
    )
    
    # Calculate total stock
    total_stock = sum(variant.stock_quantity for variant in product.variants.all())
    
    return render(request, "products/product_detail.html", {
        "product": product,
        "total_stock": total_stock,
        "title": f"{product.name} - Details"
    })

# Manager only views
@login_required
@user_passes_test(is_manager, login_url='users:login')
def create_product(request):
    if request.method == 'POST':
        form = ProductForm(request.POST)
        formset = ProductVariantFormSet(request.POST)
        
        if form.is_valid() and formset.is_valid():
            # Use transaction to ensure all or nothing
            with transaction.atomic():
                product = form.save()
                
                variants = formset.save(commit=False)
                for variant in variants:
                    variant.product = product
                    variant.is_active = True
                    # Don't save yet - we need to handle stock properly
                    
                    # Save variant first with stock_quantity = 0
                    initial_stock = variant.stock_quantity
                    variant.stock_quantity = 0
                    variant.save()
                    
                    # Create inventory entry if initial stock > 0
                    # This will automatically update the variant's stock_quantity
                    if initial_stock > 0:
                        from inventory.models import StockEntry
                        StockEntry.objects.create(
                            variant=variant,
                            quantity=initial_stock,
                            entry_type='ADDITION',
                            entered_by=request.user,
                            notes=f'Initial stock for {product.name} - {variant.variant_name}'
                        )
                
                messages.success(
                    request, 
                    f'Product "{product.name}" created with {len(variants)} variant(s) and initial stock recorded.'
                )
                return redirect('products:product_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ProductForm()
        formset = ProductVariantFormSet()

    return render(request, 'products/create_product.html', {
        'form': form,
        'formset': formset,
        'title': 'Create Product'
    })

@login_required
@user_passes_test(is_manager, login_url='users:login')
def update_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    
    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)
        formset = ProductVariantFormSet(request.POST, instance=product)
        
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                form.save()
                
                # Get existing variants before saving formset
                existing_variants = {v.id: v.stock_quantity for v in product.variants.all()}
                
                variants = formset.save(commit=False)
                
                # Handle new and updated variants
                for variant in variants:
                    old_stock = existing_variants.get(variant.id, 0) if variant.id else 0
                    form_stock = variant.stock_quantity
                    
                    # If it's an existing variant
                    if variant.id:
                        # Calculate the difference
                        difference = form_stock - old_stock
                        
                        # Save the variant first without changing stock
                        variant.stock_quantity = old_stock
                        variant.save()
                        
                        # If stock changed, create adjustment entry
                        if difference != 0:
                            from inventory.models import StockEntry
                            StockEntry.objects.create(
                                variant=variant,
                                quantity=difference,
                                entry_type='ADJUSTMENT',
                                entered_by=request.user,
                                notes=f'Stock adjustment for {product.name} - {variant.variant_name}'
                            )
                    else:
                        # New variant - save with stock = 0 first
                        initial_stock = variant.stock_quantity
                        variant.stock_quantity = 0
                        variant.save()
                        
                        # Then create entry if there's initial stock
                        if initial_stock > 0:
                            from inventory.models import StockEntry
                            StockEntry.objects.create(
                                variant=variant,
                                quantity=initial_stock,
                                entry_type='ADDITION',
                                entered_by=request.user,
                                notes=f'Initial stock for new variant {product.name} - {variant.variant_name}'
                            )
                
                # Handle deleted variants
                for variant in formset.deleted_objects:
                    variant.delete()
                    
            messages.success(request, f'Product "{product.name}" updated successfully.')
            return redirect('products:product_detail', pk=pk)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ProductForm(instance=product)
        formset = ProductVariantFormSet(instance=product)

    context = {
        'form': form,
        'formset': formset,
        'product': product,
        'title': f'Update {product.name}',
        'button_label': 'Update Product'
    }
    return render(request, 'products/create_product.html', context)

@login_required
@user_passes_test(is_manager, login_url="users:login")
def delete_product(request, pk):
    product = get_object_or_404(Product, pk=pk)

    # Check if product has sales or orders
    has_sales = product.variants.filter(sale_items__isnull=False).exists()
    has_orders = product.variants.filter(order_items__isnull=False).exists()
    
    if has_sales or has_orders:
        messages.error(
            request, 
            f'Cannot delete "{product.name}". It has associated sales or orders. '
            'Consider marking it as inactive instead.'
        )
        return redirect('products:product_detail', pk=pk)

    if request.method == "POST":
        product_name = product.name
        product.delete()
        messages.success(request, f'Product "{product_name}" deleted successfully.')
        return redirect("products:product_list")

    return render(request, "products/delete_product.html", {
        "product": product,
        "title": f"Delete {product.name}"
    })

# Category Management
@login_required
@user_passes_test(is_manager, login_url='users:login')
def category_unit_list(request):
    categories = Category.objects.filter(is_active=True).order_by('name')
    units = Unit.objects.filter(is_active=True).order_by('name')
    
    context = {
        'categories': categories,
        'units': units,
        'title': 'Categories and Units'
    }
    return render(request, 'products/category_unit_list.html', context)

@login_required
@user_passes_test(is_manager, login_url='login_user')
def create_category(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save()
            messages.success(request, f'Category "{category.name}" created successfully.')
            return redirect('products:category_unit_list')
    else:
        form = CategoryForm()
    
    return render(request, 'products/create_category.html', {
        'form': form,
        'title': 'Create Category'
    })

@login_required
@user_passes_test(is_manager, login_url='users:login')
def update_category(request, pk):
    category = get_object_or_404(Category, pk=pk)
    
    if request.method == "POST":
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, f'Category "{category.name}" updated.')
            return redirect("products:category_unit_list")
    else:
        form = CategoryForm(instance=category)
    
    return render(request, "products/create_category.html", {
        "form": form,
        "category": category,
        "title": f"Update {category.name}",
        "button_label": "Update Category"
    })

@login_required
@user_passes_test(is_manager, login_url='users:login')
def delete_category(request, pk):
    category = get_object_or_404(Category, pk=pk)
    
    # Check if category has products
    products_count = category.products.count()
    if products_count > 0:
        messages.error(
            request,
            f'Cannot delete "{category.name}". It has {products_count} associated products.'
        )
        return redirect("products:category_unit_list")
    
    if request.method == "POST":
        category_name = category.name
        category.delete()
        messages.success(request, f'Category "{category_name}" deleted.')
        return redirect("products:category_unit_list")
    
    return render(request, "products/delete_category.html", {
        "category": category,
        "title": f"Delete {category.name}"
    })

# Unit Management
@login_required
@user_passes_test(is_manager, login_url='users:login')
def create_unit(request):
    if request.method == 'POST':
        form = UnitForm(request.POST)
        if form.is_valid():
            unit = form.save()
            messages.success(request, f'Unit "{unit.name}" created successfully.')
            return redirect('products:category_unit_list')
    else:
        form = UnitForm()
    
    return render(request, 'products/create_category.html', {
        'form': form,
        'title': 'Create Unit'
    })

@login_required
@user_passes_test(is_manager, login_url='users:login')
def update_unit(request, pk):
    unit = get_object_or_404(Unit, pk=pk)
    
    if request.method == "POST":
        form = UnitForm(request.POST, instance=unit)
        if form.is_valid():
            form.save()
            messages.success(request, f'Unit "{unit.name}" updated.')
            return redirect("products:category_unit_list")
    else:
        form = UnitForm(instance=unit)
    
    return render(request, "products/create_category.html", {
        "form": form,
        "unit": unit,
        "title": f"Update {unit.name}",
        "button_label": "Update Unit"
    })

@login_required
@user_passes_test(is_manager, login_url='users:login')
def delete_unit(request, pk):
    unit = get_object_or_404(Unit, pk=pk)
    
    # Check if unit has products
    products_count = unit.products.count()
    if products_count > 0:
        messages.error(
            request,
            f'Cannot delete "{unit.name}". It has {products_count} associated products.'
        )
        return redirect("products:category_unit_list")
    
    if request.method == "POST":
        unit_name = unit.name
        unit.delete()
        messages.success(request, f'Unit "{unit_name}" deleted.')
        return redirect("products:category_unit_list")
    
    return render(request, "products/delete_unit.html", {
        "unit": unit,
        "title": f"Delete {unit.name}"
    })