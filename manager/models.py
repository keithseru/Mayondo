from django.db import models

class BusinessMetrics(models.Model):
    """Store daily business metrics for reporting"""
    date = models.DateField(unique=True)
    total_sales = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_orders = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    inventory_value = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date']
        verbose_name = 'Business Metric'
        verbose_name_plural = 'Business Metrics'
    
    def __str__(self):
        return f"Metrics for {self.date}"