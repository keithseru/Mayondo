from django.contrib import admin
from .models import Category, Unit, Product, ProductVariant

# Register your models here.
admin.site.register(Category)
admin.site.register(Unit)
admin.site.register(Product)
admin.site.register(ProductVariant)