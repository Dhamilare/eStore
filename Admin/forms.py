from django import forms
from django.utils.text import slugify
from django.core.exceptions import ValidationError
from eCommApp.models import Category, Product
from django.contrib.auth.forms import AuthenticationForm

class AdminLoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control rounded-pill px-4 py-3 mb-3',
            'placeholder': 'Username',
            'autocomplete': 'username',
            'aria-label': 'Username'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control rounded-pill px-4 py-3 mb-3',
            'placeholder': 'Password',
            'autocomplete': 'current-password',
            'aria-label': 'Password'
        })
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = ''
        self.fields['password'].label = ''
        for field_name, field in self.fields.items():
            pass

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'slug']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control rounded-pill px-4 py-3',
                'placeholder': 'Category Name'
            }),
            'slug': forms.TextInput(attrs={
                'class': 'form-control rounded-pill px-4 py-3',
                'placeholder': 'Category Slug (auto-generated if empty)',
            }),
        }
    
    def clean_slug(self):
        slug = self.cleaned_data.get('slug')
        name = self.cleaned_data.get('name')

        if not slug and name:
            slug = slugify(name)
        elif slug:
            slug = slugify(slug) 

        if not slug: 
            raise ValidationError("Slug cannot be empty. Please provide a name or a slug.")

        queryset = Category.objects.all()
        if self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        
        if queryset.filter(slug=slug).exists():
            raise ValidationError("This slug is already in use by another category. Please choose a different name or slug.")
            
        return slug


class ProductAdminForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['category', 'name', 'price', 'discount_price', 'description', 'image', 'slug', 'stock', 'available']
        widgets = {
            'category': forms.Select(attrs={'class': 'form-select rounded-pill px-4 py-3'}),
            'name': forms.TextInput(attrs={'class': 'form-control rounded-pill px-4 py-3', 'placeholder': 'Product Name'}),
            'price': forms.NumberInput(attrs={'class': 'form-control rounded-pill px-4 py-3', 'placeholder': 'Price', 'step': '0.01'}),
            'discount_price': forms.NumberInput(attrs={'class': 'form-control rounded-pill px-4 py-3', 'placeholder': 'Discount Price (optional)', 'step': '0.01'}),
            'description': forms.Textarea(attrs={'class': 'form-control rounded-3 px-4 py-3', 'placeholder': 'Product Description', 'rows': 4}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}), # For file input, standard Bootstrap input is fine
            'slug': forms.TextInput(attrs={'class': 'form-control rounded-pill px-4 py-3', 'placeholder': 'Product Slug (auto-generated if empty)'}),
            'stock': forms.NumberInput(attrs={'class': 'form-control rounded-pill px-4 py-3', 'placeholder': 'Stock Quantity', 'min': '0'}),
            'available': forms.CheckboxInput(attrs={'class': 'form-check-input ms-2'}),
        }
    
    def clean_slug(self):
        slug = self.cleaned_data.get('slug')
        name = self.cleaned_data.get('name')

        if not slug and name:
            slug = slugify(name)
        elif slug:
            slug = slugify(slug) 

        if not slug: 
            raise ValidationError("Slug cannot be empty. Please provide a name or a slug.")

        queryset = Product.objects.all()
        if self.instance.pk: 
            queryset = queryset.exclude(pk=self.instance.pk)
        
        if queryset.filter(slug=slug).exists():
            raise ValidationError("This slug is already in use. Please choose a different name or slug.")
            
        return slug

    def clean(self):
        cleaned_data = super().clean()
        price = cleaned_data.get('price')
        discount_price = cleaned_data.get('discount_price')

        if discount_price is not None and price is not None:
            if discount_price > price:
                self.add_error('discount_price', 'Discount price cannot be greater than the regular price.')
            if discount_price < 0:
                 self.add_error('discount_price', 'Discount price cannot be negative.')
        
        if price is not None and price < 0:
            self.add_error('price', 'Price cannot be negative.')

        return cleaned_data

