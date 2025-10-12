from django.db import models
from django.core.exceptions import ValidationError

# Create your models here.
class Category(models.Model):
    '''Product Categories'''
    TYPE_CHOICES = [
        ('FURNITURE', 'Furniture'),
        ('WOOD', 'Wood'),
    ]
    
    name = models.CharField(max_length=100, unique=True)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='FURNITURE')
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = 'Category'
        verbose_name_plural = 'Cartegories'
        
    def __str__(self):
        return f'{self.name} ({self.get_type_display()})'

class Unit(models.Model):
    '''Measurement units'''
    name = models.CharField(max_length=50, unique=True)
    abbreviation = models.CharField(max_length=10, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.abbreviation if self.abbreviation else self.name
    
class Product(models.Model):
    '''Base product model'''
    name = models.CharField(max_length=100)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='products')
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT, related_name='products')
    supplier = models.ForeignKey('orders.Supplier', on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        unique_together = [['name', 'category']]
        
    def __str__(self):
        return f'{self.name} {self.category.name}'

class ProductVariant(models.Model):
    '''Product variants with prices'''
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    variant_name = models.CharField(max_length=100)
    price = models.IntegerField(default=0)
    stock_quantity = models.PositiveIntegerField(default=0)
    reorder_level = models.PositiveIntegerField(default=5)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['product__name', 'variant_name']
        unique_together = [['product', 'variant_name']]
        
    def __str__(self):
        return f'{self.product.name} - {self.variant_name}'
    
    @property
    def needs_reorder(self):
        return self.stock_quantity <= self.reorder_level
    
    @property
    def is_in_stock(self):
        return self.stock_quantity > 0
    
    def add_stock(self, quantity):
        if quantity <= 0:
            raise ValueError('Qunatity must be positive')
        self.stock_quantity += quantity
        self.save(update_fields=['stock_quantity', 'updated_at'])
    
    def reduce_stock(self, quantity):
        if quantity <= 0:
            raise ValueError('Quantity must be positive')
        if quantity > self.stock_quantity:
            raise ValueError(f'Insufficient stock. Available: {self.stock_quantity}')
        self.stock_quantity -= quantity
        self.save(update_fields=['stock_quantity', 'updated_at'])