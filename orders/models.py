from django.db import models
from django.core.validators import MinValueValidator
from users.models import Employee

class Supplier(models.Model):
    '''Supplier Information'''
    name = models.CharField(max_length=100, unique=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    contact_person  = models.CharField(max_length=100)
    address = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name

class Order(models.Model):
    '''Purchase Order'''  
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('DELIVERED', 'Delivered'),
        ('PARTIAL', 'Partially Delivered'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name='orders')
    order_date = models.DateTimeField(auto_now_add=True)
    expected_delivery = models.DateField(null=True, blank=True)
    created_by = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, related_name='created_orders')
    received_by = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name='confirmed_orders')
    received_date = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-order_date']
    
    def __str__(self):
        return f'Order #{self.id} - {self.supplier.name}'
    
    @property
    def total_amount(self):
        return sum(item.subtotal for item in self.items.all())
    
    
class OrderItem(models.Model):
    '''Order Line items'''
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    variant = models.ForeignKey('products.ProductVariant', on_delete=models.PROTECT, related_name='order_items')
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    delivered_quantity = models.PositiveIntegerField(default=0)
    unit_price = models.IntegerField()
    is_delivered = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f'{self.variant} - {self.quantity} ordered'
    
    @property
    def subtotal(self):
        return self.quantity * self.unit_price
    
    def mark_as_delivered(self, quantity=None):
        if quantity is None:
            quantity = self.quantity - self.delivered_quantity
        self.delivered_quantity += quantity
        self.is_delivered = (self.delivered_quantity >= self.quantity)
        self.save()
        self.variant.add_stock(quantity)