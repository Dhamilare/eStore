from decimal import Decimal
from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.urls import reverse
from django_countries.fields import CountryField
from phonenumber_field.modelfields import PhoneNumberField
from django.utils import timezone
from django.db.models import Avg
from django.core.exceptions import ValidationError
from django.conf import settings


def send_order_status_update_email(order, new_status):
    print(f"Email sent to {order.user.email if order.user else 'Anonymous'} for Order #{order.id}. New status: {new_status}")


# --- Product Catalog Models ---
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('products_list') + f'?category={self.slug}'


class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='products')
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='product_images/', default='product_images/default.jpg')
    slug = models.SlugField(null=True, blank=True, unique=True)
    stock = models.PositiveIntegerField(default=0)
    available = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("product_detail", kwargs={"slug": self.slug})

    def get_display_price(self):
        if self.discount_price and self.discount_price < self.price:
            return self.discount_price
        return self.price

    def get_discount_percentage(self):
        if self.discount_price and self.discount_price < self.price:
            return round(((self.price - self.discount_price) / self.price) * 100)
        return 0

    @property
    def average_rating(self):
        avg = self.ratings.aggregate(avg_rating=Avg('value'))['avg_rating']
        return round(avg, 1) if avg else 0

    @property
    def total_ratings(self):
        return self.ratings.count()


class Rating(models.Model):
    product = models.ForeignKey(Product, related_name='ratings', on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    value = models.IntegerField(choices=[(i, str(i)) for i in range(1, 6)])
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('product', 'user')
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.product.name} - {self.value} stars by {self.user.username}'


class Customer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    email = models.EmailField(blank=True, null=True)
    first_name = models.CharField(max_length=50, blank=True, null=True)
    last_name = models.CharField(max_length=50, blank=True, null=True)
    date_joined = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.username

    def save(self, *args, **kwargs):
        if not self.email:
            self.email = self.user.email
        if not self.first_name:
            self.first_name = self.user.first_name
        if not self.last_name:
            self.last_name = self.user.last_name
        super().save(*args, **kwargs)

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.user.get_full_name()

    def get_phone_number(self):
        billing = BillingAddress.objects.filter(email=self.email).first()
        return billing.phone if billing else "N/A"


class BillingAddress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='billing_addresses')
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    email = models.EmailField()
    address = models.TextField()
    city = models.CharField(max_length=50)
    zipcode = models.CharField(max_length=20)
    phone = PhoneNumberField(region='NG')
    country = CountryField()
    order_note = models.TextField(null=True, blank=True)
    is_default = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = "Billing Addresses"

    def __str__(self):
        return f"{self.first_name} {self.last_name}, {self.address}, {self.city}"

class Payment(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reference = models.CharField(max_length=100, unique=True)
    paid_date = models.DateTimeField(auto_now_add=True)
    payment_gateway = models.CharField(max_length=20, choices=[
        ('PAYSTACK', 'Paystack'),
        ('STRIPE', 'Stripe'),
        ('PAYPAL', 'PayPal'),
    ], default='PAYSTACK')
    card_brand = models.CharField(max_length=20, choices=[
        ('VISA', 'Visa'),
        ('MASTERCARD', 'Mastercard'),
        ('AMEX', 'American Express'),
        ('DISCOVER', 'Discover'),
        ('UNKNOWN', 'Unknown'),
    ], blank=True, null=True)
    card_last_four = models.CharField(max_length=4, blank=True, null=True)

    class Meta:
        ordering = ['-paid_date']

    def __str__(self):
        return f'Payment {self.reference} by {self.user.username if self.user else "Anonymous"}'


class Order(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('SHIPPED', 'Shipped'),
        ('DELIVERED', 'Delivered'),
        ('CANCELLED', 'Cancelled'),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    billing_address = models.ForeignKey(BillingAddress, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    payment = models.OneToOneField(Payment, on_delete=models.SET_NULL, null=True, blank=True, related_name='order')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    ordered = models.BooleanField(default=False)
    ordered_date = models.DateTimeField(default=timezone.now)
    start_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-ordered_date']
        indexes = [models.Index(fields=['ordered', 'status'])]

    def __str__(self):
        return f"Order #{self.id} by {self.user.username if self.user else 'Anonymous'}"

    def get_total_price(self):
        return sum(item.get_final_price() for item in self.order_items.all())

    def get_shipping(self):
        return settings.SHIPPING_COST

    def get_tax(self):
        return self.get_total_price() * settings.TAX_RATE

    def get_grand_total(self):
        return self.get_total_price() + self.get_shipping() + self.get_tax()


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='order_items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, related_name='order_items', on_delete=models.SET_NULL, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['product__name']

    def __str__(self):
        return f"{self.quantity} x {self.product.name if self.product else 'Deleted Product'}"

    def get_total_product_price(self):
        return self.quantity * self.price

    def get_final_price(self):
        return self.get_total_product_price()


class Cart(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='cart'
    )
    session_key = models.CharField(
        max_length=40,
        null=True,
        blank=True,
        db_index=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        if self.user:
            return f"Cart ({self.user.username})"
        return f"Cart (Session {self.session_key or self.pk})"

    def get_total_items(self):
        return self.items.count()

    def get_total_quantity(self):
        return sum(item.quantity for item in self.items.all())

    def get_total_cost(self):
        return sum(item.get_cost() for item in self.items.all())

    def clear(self):
        self.items.all().delete()

    def clean(self):
        if not self.user and not self.session_key:
            raise ValidationError("A cart must be linked to a user or a session_key — both cannot be null.")

    def save(self, *args, **kwargs):
        self.full_clean()  # ensures the clean() check runs
        super().save(*args, **kwargs)

class CartItem(models.Model):
    cart = models.ForeignKey(
        Cart,
        related_name='items',
        on_delete=models.CASCADE
    )
    product = models.ForeignKey(
        'Product',
        on_delete=models.CASCADE
    )
    quantity = models.PositiveIntegerField(default=1)
    price_at_addition = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )

    class Meta:
        unique_together = ('cart', 'product')
        ordering = ['product__name']

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"

    def get_cost(self):
        return (self.price_at_addition or self.product.get_display_price()) * self.quantity

    def save(self, *args, **kwargs):
        if self.price_at_addition is None:
            self.price_at_addition = self.product.get_display_price()
        super().save(*args, **kwargs)