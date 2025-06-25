from django.urls import path
from .views import *
from django.contrib.auth.views import LogoutView
    

urlpatterns = [
    # Login/Logout
    path('', AdminLoginView.as_view(), name='admin_login'),
    path('logout/', LogoutView.as_view(next_page=reverse_lazy('admin_login')), name='admin_logout'),
    
    # Dashboard
    path('dashboard/', DashboardView.as_view(), name='dashboard'),

    # Category Management
    path('categories/', CategoryListView.as_view(), name='category_list'),
    path('categories/add/', CategoryFormView.as_view(), name='category_add'),
    path('categories/edit/<int:category_id>/', CategoryFormView.as_view(), name='category_edit'),
    path('categories/delete/', CategoryDeleteAjaxView.as_view(), name='category_delete'),
    
    # Order Management
    path('orders/', OrderListView.as_view(), name='order_list'),
    path('orders/<int:pk>/', OrderDetailView.as_view(), name='order_detail'),

    # Product Management
    path('products/', ProductListView.as_view(), name='product_list'),
    path('products/add/', ProductFormView.as_view(), name='product_add'),
    path('products/edit/<int:pk>/', ProductFormView.as_view(), name='product_edit'),
    path('products/detail/<int:pk>/', ProductDetailAdminView.as_view(), name='product_detail'), 
    path('products/delete/', ProductDeleteAjaxView.as_view(), name='product_delete'),
    path('products/<int:pk>/ratings/', ProductRatingListView.as_view(), name='product_ratings'),
    path('ratings/delete/', RatingDeleteAjaxView.as_view(), name='rating_delete'),

    # Customer Management
    path('customers/', CustomerListView.as_view(), name='customer_list'), 
    
]
