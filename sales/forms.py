from django import forms
from django.forms import inlineformset_factory
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column, Field
from .models import Sale, SaleItem, Customer
from products.models import ProductVariant

# Customer Form
class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ['first_name', 'last_name', 'email', 'phone', 'address']
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3})
        }
        labels = {
            'phone': 'Phone Number',
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Row(
                Column('first_name', css_class='form-group col-md-6 mb-3'),
                Column('last_name', css_class='form-group col-md-6 mb-3'),
            ),
            Row(
                Column('email', css_class='form-group col-md-6 mb-3'),
                Column('phone', css_class='form-group col-md-6 mb-3'),
            ),
            'address,',
            Submit('submit', 'Save Customer', css_class= 'btn btn-primary mt-3')
        )
        

# Sale Form
class SaleForm(forms.ModelForm):
    class Meta:
        model = Sale
        fields = ['customer', 'payment_method', 'delivery_required', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3})
        }
        
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            #ONly show active customers
            self.fields['customer'].queryset = Customer.objects.filter(is_active=True).order_by('last_name', 'first_name')
            self.fields['customer'].label_from_instance = lambda obj: f"{obj.full_name} - {obj.phone or obj.email}"
            
            self.helper = FormHelper()
            self.helper.form_method = 'post'
            self.helper.layout = Layout(
                'customer',
                Row(
                    Column('payment_method', css_class='form-group col-md-6 mb-3'),
                    Column(
                        Field('delivery_required', css_class='form-check-input'),
                        css_class='form-group col-md-6 mb-3'
                    ),
                ),
                'notes',
            )
            
class SaleItemForm(forms.ModelForm):
    class Meta:
        model = SaleItem
        fields = ['product_variant', 'quantity', 'unit_price', 'discount_percentage']
        widget = {
            'discount_percentage': forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'max': '99.99'}),
        }
        
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            # Only show active variants that are in stock
            self.field['product_variant'].query_set = ProductVariant.objects.filter(
                is_active = True,
                stock_qunatity__gt=0
            ).select_related('product', 'product_category')
            
            # Custom label showing product name, variant, price and stock
            self.field['product_variant'].label_from_instance = lambda obj: (
                f'{obj.product.name} - {obj.variant_name}'
                f'UGX {obj.price}, Stock: {obj.stock_quantity})'
            )
            
            # Set initial unit price from variant price
            if self.instance and self.instance.product_variant:
                self.fields['unit_price'].initial = self.instance.product_variant.price
    
        def clean(self):
            cleaned_data = super().clean()
            product_variant = cleaned_data.get('product_variant')
            quantity = cleaned_data.get('quantity')
            
            if product_variant and quantity:
                if quantity > product_variant.stock_quantity:
                    raise forms.ValidationError(
                        f'Only {product_variant.stock_quantity} units available for {product_variant}'
                    )
            
            return cleaned_data

# Formse for sale items
SaleItemFormset = inlineformset_factory(
    Sale,
    SaleItem,
    form = SaleItemForm,
    fields=['product_variant', 'quantity', 'unit_price', 'discount_percentage'],
    extra=3,
    can_delete=True,
    min_num=1,
    validate_min=True,
)