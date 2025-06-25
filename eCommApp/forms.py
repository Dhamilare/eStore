from django import forms
from django.contrib.auth.forms import (
    AuthenticationForm, UserCreationForm,
    PasswordResetForm, SetPasswordForm
)
from django.contrib.auth import get_user_model

from phonenumber_field.formfields import PhoneNumberField

from .models import BillingAddress, Rating

User = get_user_model()

class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label="Email or Username",
        widget=forms.TextInput(attrs={
            'class': 'form-control rounded-pill px-4 py-3',
            'placeholder': 'Enter email or username',
            'required': True,
        })
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control rounded-pill px-4 py-3',
            'placeholder': 'Enter password',
            'required': True,
        })
    )
    remember_me = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label="Remember me",
    )


class RegisterForm(UserCreationForm):

    first_name = forms.CharField(
        max_length=50, required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control rounded-pill px-4 py-3',
            'placeholder': 'First name',
        })
    )
    last_name = forms.CharField(
        max_length=50, required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control rounded-pill px-4 py-3',
            'placeholder': 'Last name',
        })
    )
    email = forms.EmailField(
        max_length=254, required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control rounded-pill px-4 py-3',
            'placeholder': 'Email address',
        })
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['username'].widget = forms.TextInput(attrs={
            'class': 'form-control rounded-pill px-4 py-3',
            'placeholder': 'Username (e.g. john_doe)',
            'required': True,
        })
        self.fields['password1'].widget = forms.PasswordInput(attrs={
            'class': 'form-control rounded-pill px-4 py-3',
            'placeholder': 'Password',
            'required': True,
        })
        self.fields['password2'].widget = forms.PasswordInput(attrs={
            'class': 'form-control rounded-pill px-4 py-3',
            'placeholder': 'Confirm password',
            'required': True,
        })

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("A user with that email already exists.")
        return email

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("A user with that username already exists.")
        return username

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        if commit:
            user.save()
        return user


class CustomPasswordResetForm(PasswordResetForm):
    email = forms.EmailField(
        label="Email address", max_length=254,
        widget=forms.EmailInput(attrs={
            'autocomplete': 'email',
            'class': 'form-control rounded-pill px-4 py-3',
            'placeholder': 'Enter your email address',
        })
    )


class CustomSetPasswordForm(SetPasswordForm):
    new_password1 = forms.CharField(
        label="New password", strip=False,
        widget=forms.PasswordInput(attrs={
            'autocomplete': 'new-password',
            'class': 'form-control rounded-pill px-4 py-3',
            'placeholder': 'Enter new password',
        }),
        help_text=(
            "<ul>"
            "<li>Must be at least 8 characters.</li>"
            "<li>Cannot be too similar to your personal information.</li>"
            "<li>Cannot be a commonly used password or all numeric.</li>"
            "</ul>"
        )
    )
    new_password2 = forms.CharField(
        label="Confirm new password", strip=False,
        widget=forms.PasswordInput(attrs={
            'autocomplete': 'new-password',
            'class': 'form-control rounded-pill px-4 py-3',
            'placeholder': 'Confirm new password',
        })
    )


class CheckoutForm(forms.ModelForm):
    phone = PhoneNumberField(
        region='NG',
        widget=forms.TextInput(attrs={
            'class': 'form-control rounded-pill px-4 py-3',
            'placeholder': 'e.g. +2348012345678',
        })
    )

    class Meta:
        model = BillingAddress
        fields = [
            'first_name', 'last_name', 'email', 'address',
            'city', 'zipcode', 'phone', 'country', 'order_note',
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control rounded-pill px-4 py-3',
                'placeholder': 'First name',
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control rounded-pill px-4 py-3',
                'placeholder': 'Last name',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control rounded-pill px-4 py-3',
                'placeholder': 'Email address',
            }),
            'address': forms.TextInput(attrs={
                'class': 'form-control rounded-pill px-4 py-3',
                'placeholder': 'Street / apartment / suite',
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control rounded-pill px-4 py-3',
                'placeholder': 'City',
            }),
            'zipcode': forms.TextInput(attrs={
                'class': 'form-control rounded-pill px-4 py-3',
                'placeholder': 'ZIP / postal code',
            }),
            'country': forms.Select(attrs={
                'class': 'form-control rounded-pill px-4 py-3',
            }),
            'order_note': forms.Textarea(attrs={
                'class': 'form-control rounded-3 px-4 py-3',
                'placeholder': 'Order notes (optional)',
                'rows': 3,
            }),
        }


class ProductRatingForm(forms.ModelForm):
    value = forms.IntegerField(
        label="Rating (1-5 stars)",
        min_value=1, max_value=5,
        widget=forms.NumberInput(attrs={
            'class': 'form-control rounded-pill px-4 py-3',
            'placeholder': '1-5',
        })
    )
    comment = forms.CharField(
        label="Review (optional)", required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control rounded-3 px-4 py-3',
            'placeholder': 'Tell us what you think…',
            'rows': 4,
        })
    )

    class Meta:
        model = Rating
        fields = ('value', 'comment')
    
