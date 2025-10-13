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
            'quantity': forms.NumberInput(attrs={
                'step': '1', 
                'class': 'form-control'
                # Removed 'min' to allow negative numbers
            }),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
        help_texts = {
            'quantity': 'Enter quantity: positive for additions, negative for reductions',
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

        if quantity == 0:
            raise forms.ValidationError('Quantity cannot be zero.')

        return quantity
    
    def clean(self):
        cleaned_data = super().clean()
        quantity = cleaned_data.get('quantity')
        variant = cleaned_data.get('variant')
        entry_type = cleaned_data.get('entry_type')

        if not variant or not entry_type or quantity is None:
            return cleaned_data
        
        # For negative adjustments, check if stock would go negative
        if quantity < 0:
            new_stock = variant.stock_quantity + quantity
            if new_stock < 0:
                raise forms.ValidationError(
                    f'Cannot reduce stock by {abs(quantity)}. '
                    f'Current stock is {variant.stock_quantity}. '
                    f'This would result in negative stock ({new_stock}).'
                )
        
        return cleaned_data