from django.contrib import admin
from .models import Supplier, Order, OrderItem

# Register your models here.
admin.site.register(Supplier)
admin.site.register(Order)
admin.site.register(OrderItem)