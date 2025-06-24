from django.contrib import admin
from django.db import transaction # For atomic operations
from django.contrib import messages # For admin messages
from .models import *
from .utils import *


# --- Inline Admin Classes (for related objects within a parent's admin page) ---

class OrderItemInline(admin.TabularInline):
    """Inline display for OrderItems within an Order."""
    model = OrderItem
    # raw_id_fields can be useful for performance with many products
    raw_id_fields = ['product']
    extra = 0 # Don't show extra empty forms by default
    fields = ('product', 'quantity', 'price') # Display these fields
    readonly_fields = ('price',) # Price should be from the time of order


class CartItemInline(admin.TabularInline):
    """Inline display for CartItems within a Cart."""
    model = CartItem
    raw_id_fields = ['product']
    extra = 0
    fields = ('product', 'quantity', 'price_at_addition')
    readonly_fields = ('price_at_addition',)


# --- Model Admin Classes ---

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Admin configuration for the Category model."""
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)} # Automatically generate slug from name
    search_fields = ['name']
    ordering = ['name'] # Order alphabetically


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """Admin configuration for the Product model."""
    list_display = ['name', 'category', 'price', 'discount_price', 'stock', 'available', 'created', 'updated']
    list_filter = ['available', 'category', 'created', 'updated']
    list_editable = ['price', 'discount_price', 'stock', 'available'] # Allow inline editing
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name', 'description']
    ordering = ['name']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Admin configuration for the Order model."""
    list_display = ['id', 'user', 'billing_address', 'payment', 'status', 'ordered', 'ordered_date']
    list_filter = ['ordered', 'status', 'ordered_date', 'payment__payment_gateway'] # Filter by payment gateway too
    search_fields = ['id__iexact', 'user__username__iexact',
                     'billing_address__email__iexact', 'billing_address__first_name', 'billing_address__last_name']
    inlines = [OrderItemInline] # Show order items inline
    date_hierarchy = 'ordered_date' # Adds a date-based navigation
    actions = ['mark_as_processing', 'mark_as_shipped', 'mark_as_delivered', 'mark_as_cancelled']

    # Readonly fields to prevent accidental changes after order is placed
    readonly_fields = ('ordered_date', 'start_date', 'payment')

    def get_queryset(self, request):
        # Optimize queryset by selecting related objects for display
        return super().get_queryset(request).select_related('user', 'billing_address', 'payment')

    def save_model(self, request, obj, form, change):
        # Store old status to detect changes
        old_status = None
        if obj.pk: # If updating an existing object
            try:
                old_obj = Order.objects.get(pk=obj.pk)
                old_status = old_obj.status
            except Order.DoesNotExist:
                pass # New object, old_status remains None

        super().save_model(request, obj, form, change) # Save the object first
        
        # Send status update email if status has changed
        if old_status and old_status != obj.status:
            try:
                send_order_status_update_email(obj, obj.status)
                messages.info(request, f"Order #{obj.id} status update email sent to customer.")
            except Exception as e:
                messages.error(request, f"Failed to send status update email for Order #{obj.id}: {e}")
                logger.error(f"Email send error for Order #{obj.id}: {e}", exc_info=True)

    # --- Custom Admin Actions ---
    def mark_as_processing(self, request, queryset):
        updated = queryset.update(status=Order.PROCESSING)
        self.message_user(request, f'{updated} orders marked as processing.')
    mark_as_processing.short_description = "Mark selected orders as Processing"

    def mark_as_shipped(self, request, queryset):
        for order in queryset:
            if order.status != Order.SHIPPED:
                order.status = Order.SHIPPED
                order.save()
        self.message_user(request, f'Selected orders marked as shipped.')
    mark_as_shipped.short_description = "Mark selected orders as Shipped"

    def mark_as_delivered(self, request, queryset):
        updated = queryset.update(status=Order.DELIVERED)
        self.message_user(request, f'{updated} orders marked as delivered.')
    mark_as_delivered.short_description = "Mark selected orders as Delivered"

    def mark_as_cancelled(self, request, queryset):
        updated = queryset.update(status=Order.CANCELLED)
        self.message_user(request, f'{updated} orders marked as cancelled.')
    mark_as_cancelled.short_description = "Mark selected orders as Cancelled"


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    """Admin configuration for the Customer model."""
    list_display = ['user', 'first_name', 'last_name', 'email', 'date_joined']
    search_fields = ['user__username', 'email', 'first_name', 'last_name']
    ordering = ['user__username']
    # You might want to make 'user' a raw_id_field for large user bases
    raw_id_fields = ['user']


@admin.register(BillingAddress)
class BillingAddressAdmin(admin.ModelAdmin):
    """Admin configuration for the BillingAddress model."""
    list_display = ['user', 'first_name', 'last_name', 'email', 'city', 'country', 'phone', 'is_default']
    list_filter = ['country', 'is_default']
    search_fields = ['first_name', 'last_name', 'email', 'address', 'city', 'zipcode', 'phone']
    ordering = ['-id']
    raw_id_fields = ['user'] # Link to User model


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    """Admin configuration for the Payment model."""
    list_display = ['id', 'user', 'amount', 'reference', 'payment_gateway', 'card_brand', 'card_last_four', 'paid_date']
    list_filter = ['payment_gateway', 'paid_date', 'card_brand']
    search_fields = ['user__username', 'reference', 'card_last_four']
    ordering = ['-paid_date']
    raw_id_fields = ['user']


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    """Admin configuration for the Cart model."""
    list_display = ['id', 'user', 'session_key', 'created_at', 'updated_at', 'get_total_quantity']
    inlines = [CartItemInline] # Show cart items inline
    search_fields = ['user__username', 'session_key']
    ordering = ['-updated_at']
    raw_id_fields = ['user'] # Link to User model

    def get_total_quantity(self, obj):
        return obj.get_total_quantity()
    get_total_quantity.short_description = 'Total Quantity'


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    """Admin configuration for the Rating model."""
    list_display = ['product', 'user', 'value', 'comment', 'created_at']
    list_filter = ['value', 'created_at']
    search_fields = ['product__name', 'user__username', 'comment']
    ordering = ['-created_at']
    raw_id_fields = ['product', 'user'] # Link to Product and User models

