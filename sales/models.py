from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import transaction
from products.models import ProductVariant
from users.models import Employee
from decimal import Decimal

class Customer(models.Model):
    '''Customer Information'''
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
    
    def __str__(self):
        return f'{self.first_name} {self.last_name}'
    
    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'
    
class Sale(models.Model):
    '''Sales Transaction'''
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

    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='sales')
    sale_date = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, related_name='sales_created')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='CASH')
    delivery_required = models.BooleanField(default=False)
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), help_text="Automatically set to 5 percent of sale total if delivery is required")
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-sale_date']
    
    def __str__(self):
        return f"Sale #{self.id} - {self.customer}"
    
    def save(self, *args, **kwargs):
        # Calculate delivery fee before saving
        item_total = sum(item.total_price() for item in self.items.all())
        self.delivery_fee = item_total * Decimal('0.05') if self.delivery_required else Decimal('0.00')
        super().save(*args, **kwargs)
    
    @property
    def total(self):
        item_total = sum(item.total_price() for item in self.items.all())
        return item_total + self.delivery_fee
    
    @transaction.atomic
    def complete_sale(self):
        if self.status == 'COMPLETED':
            raise ValidationError('Sale is already completed')
        
        # Validate stock
        for item in self.items.all():
            if item.quantity > item.product_variant.stock:
                raise ValidationError(f'Insufficient stock for {item.product_variant}')
        
        # Deduct stock
        for item in self.items.all():
            item.product_variant.reduce_stock(item.quantity)
            from inventory.models import StockMovement
            StockMovement.create_movement(
                variant=item.product_variant,
                movement_type = 'SALE',
                quantity=-item.quantity,
                performed_by=self.created_by,
                reference_id=f'SALE-{self.id}'
            )
        self.status = 'COMPLETED'
        self.save()
    
class SaleItem(models.Model):
    """Sale line items"""
    sale = models.ForeignKey(Sale, related_name='items', on_delete=models.CASCADE)
    product_variant = models.ForeignKey(ProductVariant, on_delete=models.PROTECT, related_name='sale_items')
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    unit_price = models.IntegerField()
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.quantity} x {self.product_variant}"
    
    def total_price(self):
        subtotal = self.quantity * self.unit_price
        discount = subtotal * (self.discount_percentage / Decimal('100'))
        return subtotal + - discount
    
    def save(self, *args, **kwargs):
        if not self.unit_price:
            self.unit_price = self.product_variant.price
        super().save(*args, **kwargs)
    