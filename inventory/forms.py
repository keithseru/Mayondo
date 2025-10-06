from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column
from .models import StockEntry
from products.models import ProductVariant

class StockEntryForm(forms.ModelForm):
    class Meta:
        model = StockEntry
        fields = ['variant', 'quantity', 'entry_type', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
        help_texts = {
            'quantity': 'Enter positive number to add stock, negative number to reduce stock',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Only show active variants
        self.fields['variant'].queryset = ProductVariant.objects.filter(
            is_active=True
        ).select_related('product', 'product__category').order_by('product__name', 'variant_name')
        
        # Custom label showing product, variant, current stock and price
        self.fields['variant'].label_from_instance = lambda obj: (
            f"{obj.product.name} - {obj.variant_name} "
            f"(Stock: {obj.stock_quantity}, Price: UGX {obj.price:,})"
        )
        
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            'variant',
            Row(
                Column('quantity', css_class='form-group col-md-6 mb-3'),
                Column('entry_type', css_class='form-group col-md-6 mb-3'),
            ),
            'notes',
            Submit('submit', 'Record Stock Entry', css_class='btn btn-primary mt-3')
        )
    
    def clean_quantity(self):
        quantity = self.cleaned_data.get('quantity')
        variant = self.cleaned_data.get('variant')
        
        if quantity == 0:
            raise forms.ValidationError('Quantity cannot be zero')
        
        # Check if reduction would result in negative stock
        if quantity < 0 and variant:
            new_stock = variant.stock_quantity + quantity
            if new_stock < 0:
                raise forms.ValidationError(
                    f'Cannot reduce stock by {abs(quantity)}. '
                    f'Current stock is {variant.stock_quantity}. '
                    f'This would result in negative stock ({new_stock}).'
                )
        
        return quantity