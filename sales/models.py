from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import transaction
from decimal import Decimal
from products.models import ProductVariant
from users.models import Employee

class Customer(models.Model):
    """Customer Information"""
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['last_name', 'first_name']
        verbose_name = 'Customer'
        verbose_name_plural = 'Customers'
    
    def __str__(self):
        return f'{self.first_name} {self.last_name}'
    
    def clean(self):
        """Validate customer data"""
        super().clean()
        if not self.email and not self.phone:
            raise ValidationError('Either email or phone number must be provided')
    
    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'
    
    @property
    def total_purchases(self):
        """Calculate total amount of all completed purchases"""
        return sum(sale.total for sale in self.sales.filter(status='COMPLETED'))
    
    @property
    def purchase_count(self):
        """Count number of completed purchases"""
        return self.sales.filter(status='COMPLETED').count()


class Sale(models.Model):
    """Sales Transaction"""
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    PAYMENT_METHODS = [
        ('CASH', 'Cash'),
        ('MOBILE_MONEY', 'Mobile Money'),
        ('BANK_TRANSFER', 'Bank Transfer'),
        ('CARD', 'Card Payment'),
    ]

    customer = models.ForeignKey(
        Customer, 
        on_delete=models.PROTECT, 
        related_name='sales'
    )
    sale_date = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        Employee, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='sales_created'
    )
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='PENDING'
    )
    payment_method = models.CharField(
        max_length=20, 
        choices=PAYMENT_METHODS, 
        default='CASH'
    )
    delivery_required = models.BooleanField(
        default=False,
        help_text="Check if customer needs delivery"
    )
    delivery_fee = models.PositiveIntegerField(
        default=0,
        help_text="Automatically calculated as 5% of subtotal if delivery is required (in UGX)"
    )
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-sale_date']
        verbose_name = 'Sale'
        verbose_name_plural = 'Sales'
    
    def __str__(self):
        return f"Sale #{self.id} - {self.customer.full_name}"
    
    def clean(self):
        """Validate sale"""
        super().clean()
        if self.status == 'COMPLETED' and not self.items.exists():
            raise ValidationError('Cannot complete sale without items')
    
    def calculate_subtotal(self):
        """Calculate subtotal of all items (before delivery fee)"""
        return sum(item.total_price() for item in self.items.all())
    
    def calculate_delivery_fee(self):
        """Calculate delivery fee (5% of subtotal, rounded to nearest UGX)"""
        if self.delivery_required:
            subtotal = self.calculate_subtotal()
            # Calculate 5% and round to nearest integer
            return int(round(subtotal * 0.05))
        return 0
    
    def update_delivery_fee(self):
        """Update delivery fee based on current items"""
        self.delivery_fee = self.calculate_delivery_fee()
        self.save(update_fields=['delivery_fee', 'updated_at'])
    
    @property
    def subtotal(self):
        """Subtotal of all items (without delivery fee) in UGX"""
        return self.calculate_subtotal()
    
    @property
    def total(self):
        """Total amount including delivery fee in UGX"""
        return self.calculate_subtotal() + self.delivery_fee
    
    @property
    def item_count(self):
        """Count total items in sale"""
        return sum(item.quantity for item in self.items.all())
    
    @property
    def total_formatted(self):
        """Format total with thousand separators (e.g., 1,500,000)"""
        return f"UGX {self.total:,}"
    
    @transaction.atomic
    def complete_sale(self):
        """
        Complete the sale and update inventory
        This should be called when payment is confirmed
        """
        if self.status == 'COMPLETED':
            raise ValidationError('Sale is already completed')
        
        if not self.items.exists():
            raise ValidationError('Cannot complete sale without items')
        
        # Update delivery fee before completing
        self.delivery_fee = self.calculate_delivery_fee()
        
        # Validate stock availability for all items
        for item in self.items.all():
            if item.product_variant.stock_quantity < item.quantity:
                raise ValidationError(
                    f'Insufficient stock for {item.product_variant}. '
                    f'Available: {item.product_variant.stock_quantity}, '
                    f'Required: {item.quantity}'
                )
        
        # Deduct stock for all items
        for item in self.items.all():
            item.product_variant.reduce_stock(item.quantity)
            
            # Create stock movement record
            from inventory.models import StockMovement
            StockMovement.create_movement(
                variant=item.product_variant,
                movement_type='SALE',
                quantity=-item.quantity,
                performed_by=self.created_by,
                reference_id=f'SALE-{self.id}',
                notes=f'Sale to {self.customer.full_name}'
            )
        
        self.status = 'COMPLETED'
        self.save()
    
    @transaction.atomic
    def cancel_sale(self):
        """
        Cancel the sale and restore inventory if it was completed
        """
        if self.status == 'CANCELLED':
            raise ValidationError('Sale is already cancelled')
        
        # If sale was completed, restore stock
        if self.status == 'COMPLETED':
            for item in self.items.all():
                item.product_variant.add_stock(item.quantity)
                
                # Create stock movement record
                from inventory.models import StockMovement
                StockMovement.create_movement(
                    variant=item.product_variant,
                    movement_type='RETURN',
                    quantity=item.quantity,
                    performed_by=self.created_by,
                    reference_id=f'SALE-{self.id}-CANCEL',
                    notes=f'Sale cancellation for {self.customer.full_name}'
                )
        
        self.status = 'CANCELLED'
        self.save()


class SaleItem(models.Model):
    """Sale line items"""
    sale = models.ForeignKey(
        Sale, 
        related_name='items', 
        on_delete=models.CASCADE
    )
    product_variant = models.ForeignKey(
        ProductVariant, 
        on_delete=models.PROTECT,
        related_name='sale_items'
    )
    quantity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)]
    )
    unit_price = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text="Price per unit at time of sale (in UGX)"
    )
    discount_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Discount percentage (0-99.99)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['sale', 'id']
        verbose_name = 'Sale Item'
        verbose_name_plural = 'Sale Items'
    
    def __str__(self):
        return f"{self.quantity} x {self.product_variant} at UGX {self.unit_price:,} each"
    
    def clean(self):
        """Validate sale item"""
        super().clean()
        
        if self.unit_price and self.unit_price <= 0:
            raise ValidationError({'unit_price': 'Unit price must be greater than zero'})
        
        if self.discount_percentage and self.discount_percentage >= 100:
            raise ValidationError({'discount_percentage': 'Discount cannot be 100% or more'})
    

def save(self, *args, **kwargs):
    """Set unit price from variant if not provided"""
    # Only set unit_price if not provided AND product_variant is available
    if not self.unit_price:
        try:
            if self.product_variant:
                self.unit_price = self.product_variant.price
        except:
            pass  # If product_variant not available, skip
    
    super().save(*args, **kwargs)
    
    # Update delivery fee in the parent sale after saving item
    try:
        if self.sale and self.sale.delivery_required:
            self.sale.update_delivery_fee()
    except:
        pass  # If sale not available yet, skip
    
    @property
    def subtotal(self):
        """Subtotal before discount (in UGX)"""
        return self.quantity * self.unit_price
    
    @property
    def discount_amount(self):
        """Calculate discount amount (rounded to nearest UGX)"""
        discount = float(self.subtotal) * (float(self.discount_percentage) / 100)
        return int(round(discount))
    
    def total_price(self):
        """Calculate total price with discount (in UGX)"""
        return self.subtotal - self.discount_amount
    
    @property
    def total_price_formatted(self):
        """Format total with thousand separators"""
        return f"UGX {self.total_price():,}"
    
    def save(self, *args, **kwargs):
        """Set unit price from variant if not provided"""
        if not self.unit_price and self.product_variant:
            self.unit_price = self.product_variant.price
        
        super().save(*args, **kwargs)
        
        # Update delivery fee in the parent sale after saving item
        if hasattr(self, 'sale') and self.sale and self.sale.delivery_required:
            self.sale.update_delivery_fee()