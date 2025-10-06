from django.db import models
from django.core.exceptions import ValidationError
from products.models import ProductVariant
from users.models import Employee

# Create your models here.
class StockEntry(models.Model):
    '''Manual stock adjusments'''
    ENTRY_TYPES = [
        ('ADDITION', 'Stock Addition'),
        ('ADJUSTMENT', 'Stock Adjustment'),
        ('DAMAGE', 'Damaged Goods'),
        ('RETURN', 'Customer Return'),
        ('CORRECTION', 'Inventory Correction'),
    ]
    
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name='stock_entries')
    quantity = models.IntegerField(help_text='Positive for additions, negative for reductions')
    entry_type = models.CharField(max_length=20, choices=ENTRY_TYPES, default='ADJUSTMENT')
    entry_date = models.DateTimeField(auto_now_add=True)
    entered_by = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-entry_date']
        verbose_name = 'StockEntry'
        verbose_name_plural = 'Stock Entries'
        
    def __str__(self):
        sign = '+' if self.quantity > 0 else ''
        return f'{self.variant} - {sign}{self.quantity} units'
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        if is_new:
            super.save(*args, **kwargs)
            self.variant.stock_quantity += self.quantity
            self.variant.save(update_fields=['stock_quantity', 'updated_at'])
        else:
            super().save(*args, **kwargs)

class StockMovement(models.Model):
    '''Audit trail for stock changes'''
    MOVEMENT_TYPES = [
        ('SALE', 'Sale'),
        ('ORDER', 'Purchase Order'),
        ('ADJUSTMENT', 'Manual Adjustment'),
        ('RETURN', 'Return'),
    ]
    
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name='movements')
    movement_type = models.CharField(max_length=20, choices=MOVEMENT_TYPES)
    quantity = models.IntegerField()
    reference_id = models.CharField(max_length=100, blank=True)
    previous_stock = models.PositiveIntegerField()
    new_stock = models.PositiveIntegerField()
    performed_by = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, related_name='stock_movements')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)   
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        sign = '+' if self.quantity > 0 else ''
        return f'{self.variant} - {sign}{self.quantity}'
    
    @classmethod
    def create_movement(cls, variant, movement_type, quantity, performed_by, reference_id='', notes=''):
        previous_stock = variant.stock_quantity
        new_stock = previous_stock + quantity
        return cls.objects.create(
            variant = variant,
            movement_type = movement_type,
            quantity = quantity,
            reference_id = reference_id,
            previous_stock = previous_stock,
            new_stock = new_stock,
            performed_by = performed_by,
            notes = notes
        )