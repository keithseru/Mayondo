from django import forms
from django.forms import inlineformset_factory, modelformset_factory
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column
from .models import Order, OrderItem, Supplier
from products.models import ProductVariant

class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ['name', 'contact_person', 'email', 'phone', 'address', 'notes']
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Row(
                Column('name', css_class='form-group col-md-6 mb-3'),
                Column('contact_person', css_class='form-group col-md-6 mb-3'),
            ),
            Row(
                Column('email', css_class='form-group col-md-6 mb-3'),
                Column('phone', css_class='form-group col-md-6 mb-3'),
            ),
            'address',
            'notes',
            Submit('submit', 'Save Supplier', css_class='btn btn-primary mt-3')
        )


class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['supplier', 'expected_delivery', 'notes']
        widgets = {
            'expected_delivery': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show active suppliers
        self.fields['supplier'].queryset = Supplier.objects.filter(is_active=True).order_by('name')
        
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            'supplier',
            'expected_delivery',
            'notes',
        )


class OrderItemForm(forms.ModelForm):
    class Meta:
        model = OrderItem
        fields = ['variant', 'quantity', 'unit_price', 'notes']
        widgets = {
            'notes': forms.TextInput(attrs={'placeholder': 'Optional notes'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Show all active variants
        self.fields['variant'].queryset = ProductVariant.objects.filter(
            is_active=True
        ).select_related('product', 'product__category')
        
        # Custom label
        self.fields['variant'].label_from_instance = lambda obj: (
            f"{obj.product.name} - {obj.variant_name} "
            f"(Current Stock: {obj.stock_quantity}, Price: UGX {obj.price:,})"
        )
        
        # Set initial unit price from variant if available
        if self.instance and self.instance.variant:
            self.fields['unit_price'].initial = self.instance.variant.price


# Formset for creating order items
OrderItemFormSet = inlineformset_factory(
    Order,
    OrderItem,
    form=OrderItemForm,
    fields=['variant', 'quantity', 'unit_price', 'notes'],
    extra=3,
    can_delete=True,
    min_num=1,
    validate_min=True,
)


class DeliveryForm(forms.ModelForm):
    """Form for confirming delivery of order items"""
    class Meta:
        model = OrderItem
        fields = ['delivered_quantity', 'notes']
        widgets = {
            'delivered_quantity': forms.NumberInput(attrs={'min': 0}),
            'notes': forms.TextInput(attrs={'placeholder': 'Delivery notes'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set max value for delivered_quantity
        if self.instance and self.instance.pk:
            remaining = self.instance.remaining_quantity
            self.fields['delivered_quantity'].widget.attrs['max'] = remaining
            self.fields['delivered_quantity'].help_text = f'Remaining to deliver: {remaining}'
    
    def clean_delivered_quantity(self):
        delivered_qty = self.cleaned_data.get('delivered_quantity')
        
        if delivered_qty and delivered_qty < 0:
            raise forms.ValidationError('Delivered quantity cannot be negative')
        
        if self.instance and self.instance.pk:
            if delivered_qty > self.instance.remaining_quantity:
                raise forms.ValidationError(
                    f'Cannot deliver more than ordered. '
                    f'Remaining quantity: {self.instance.remaining_quantity}'
                )
        
        return delivered_qty


# Formset for confirming deliveries
DeliveryFormSet = modelformset_factory(
    OrderItem,
    form=DeliveryForm,
    fields=['delivered_quantity', 'notes'],
    extra=0,
    can_delete=False
)