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
            'quantity': forms.NumberInput(attrs={'min': '-9999', 'step': '1', 'class': 'allow_negative'}),
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
        entry_type = self.cleaned_data.get('entry_type')

        if quantity == 0:
            raise forms.ValidationError('Quantity cannot be zero.')

        if not variant or not entry_type:
            return quantity  # Skip validation if missing context

        # Validate direction based on entry type
        if entry_type == 'DAMAGE' and quantity > 0:
            raise forms.ValidationError('Damaged goods must be entered as a negative quantity.')
        if entry_type == 'RETURN' and quantity < 0:
            raise forms.ValidationError('Customer returns must be entered as a positive quantity.')
        if entry_type == 'ADDITION' and quantity < 0:
            raise forms.ValidationError('Stock additions must be positive.')
        if entry_type == 'CORRECTION':
            # Allow both directions, but validate against stock
            new_stock = variant.stock_quantity + quantity
            if new_stock < 0:
                raise forms.ValidationError(
                    f'Correction would result in negative stock ({new_stock}). '
                    f'Current stock is {variant.stock_quantity}.'
                )

        # General check for any negative adjustment
        if quantity < 0:
            new_stock = variant.stock_quantity + quantity
            if new_stock < 0:
                raise forms.ValidationError(
                    f'Cannot reduce stock by {abs(quantity)}. '
                    f'Current stock is {variant.stock_quantity}. '
                    f'This would result in negative stock ({new_stock}).'
                )

        return quantity