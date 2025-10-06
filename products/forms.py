from django import forms
from django.forms import inlineformset_factory
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column
from .models import Product, ProductVariant, Unit, Category

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "type", "description"]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Row(
                Column('name', css_class='form-group col-md-6 mb-3'),
                Column('type', css_class='form-group col-md-6 mb-3'),
            ),
            'description',
            Submit('submit', 'Save Category', css_class='btn btn-primary mt-3')
        )


class UnitForm(forms.ModelForm):
    class Meta:
        model = Unit
        fields = ["name", "abbreviation"]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Row(
                Column('name', css_class='form-group col-md-6 mb-3'),
                Column('abbreviation', css_class='form-group col-md-6 mb-3'),
            ),
            Submit('submit', 'Save Unit', css_class='btn btn-primary mt-3')
        )


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ["name", "category", "unit", "supplier", "description"]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show active categories and units
        self.fields['category'].queryset = Category.objects.filter(is_active=True).order_by('name')
        self.fields['unit'].queryset = Unit.objects.filter(is_active=True).order_by('name')
        
        # Show active suppliers
        from orders.models import Supplier
        self.fields['supplier'].queryset = Supplier.objects.filter(is_active=True).order_by('name')
        self.fields['supplier'].required = False
        
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            'name',
            Row(
                Column('category', css_class='form-group col-md-6 mb-3'),
                Column('unit', css_class='form-group col-md-6 mb-3'),
            ),
            'supplier',
            'description',
        )


class ProductVariantForm(forms.ModelForm):
    class Meta:
        model = ProductVariant
        fields = ["variant_name", "price", "reorder_level"]
        widgets = {
            'price': forms.NumberInput(attrs={'min': 1}),
            'reorder_level': forms.NumberInput(attrs={'min': 0, 'value': 10}),
        }
        help_texts = {
            'price': 'Price in UGX (Ugandan Shillings)',
            'reorder_level': 'Alert when stock falls to this level',
        }
    
    def clean_price(self):
        price = self.cleaned_data.get('price')
        if price and price <= 0:
            raise forms.ValidationError('Price must be greater than zero')
        return price


# Formset for product variants
ProductVariantFormSet = inlineformset_factory(
    Product,
    ProductVariant,
    form=ProductVariantForm,
    fields=["variant_name", "price", "reorder_level"],
    extra=2,
    can_delete=True,
    min_num=1,
    validate_min=True,
)