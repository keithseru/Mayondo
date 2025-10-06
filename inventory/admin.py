from django.contrib import admin
from .models import StockEntry, StockMovement

# Register your models here.
admin.site.register(StockEntry)
admin.site.register(StockMovement)