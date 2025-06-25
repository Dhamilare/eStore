from django.urls import path, reverse_lazy
from django.contrib.auth import views as auth_views # Keep for password reset views

from . import views # Your custom views (including CustomLoginView, register_view, activate)
from .forms import * # Your forms (LoginForm, CustomPasswordResetForm, CustomSetPasswordForm)

urlpatterns = [
    # === Home & Content Pages ===
    path('', views.HomeView.as_view(), name='home'),
    path('products/', views.ProductListView.as_view(), name='products_list'),
    path('product_details/<slug:slug>/', views.ProductDetailView.as_view(), name='product_detail'),
    path('services/', views.services_view, name='services'),

    # === Cart & Checkout ===
    path('cart/', views.cart_view, name='cart'),
    path('checkout/', views.CheckoutView.as_view(), name='checkout'),
    path('products/<int:product_id>/review/', views.submit_review, name='submit_review'),

    # === User Authentication ===
    path('accounts/login/',
         views.CustomLoginView.as_view(
             template_name='accounts/login.html',
             authentication_form=LoginForm
         ),
         name='login'),

    path('accounts/logout/', views.customerLogout, name='logout'),

    path('accounts/register/', views.register_view, name='register'), # Your register view
    path('activate/<uidb64>/<token>/', views.activate, name='activate'), # Your activate view

    # === Password Reset Flow ===
    path('accounts/password_reset/',
         auth_views.PasswordResetView.as_view(
             template_name='accounts/password_reset.html',
             email_template_name='accounts/password_reset_email.html',
             success_url=reverse_lazy('password_reset_done'),
             form_class=CustomPasswordResetForm
         ),
         name='password_reset'),

    path('accounts/password_reset/done/',
         auth_views.PasswordResetDoneView.as_view(
             template_name='accounts/password_reset_done.html'
         ),
         name='password_reset_done'),

    path('accounts/reset/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(
             template_name='accounts/password_reset_confirm.html',
             success_url=reverse_lazy('password_reset_complete'),
             form_class=CustomSetPasswordForm
         ),
         name='password_reset_confirm'),

    path('accounts/reset/done/',
         auth_views.PasswordResetCompleteView.as_view(
             template_name='accounts/password_reset_complete.html'
         ),
         name='password_reset_complete'),

    # === Order History & Tracking ===
    path('my-orders/', views.OrderHistoryView.as_view(), name='order_history'),
    path('my-orders/invoice/<int:order_id>/', views.invoice_template_view, name='invoice'),

    # === Payments ===
    path('payment/', views.PaymentMethodsView.as_view(), name='payment'),
    path('verify-payment/', views.verifyPayment, name='verifyPayment'),
    path('success/', views.success_view, name='success'),

    # === AJAX API Endpoints ===
    path('api/cart/add/', views.add_to_cart_api, name='api_add_to_cart'),
    path('api/cart/update/', views.update_cart_item_api, name='api_update_cart_item'),
    path('api/cart/remove/', views.remove_from_cart_api, name='api_remove_from_cart'),
]