from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from .models import Cart, CartItem
from django.db import transaction

@receiver(user_logged_in)
def merge_session_cart_to_user_cart(sender, user, request, **kwargs):
    session_key = request.session.session_key
    if not session_key:
        return

    try:
        session_cart = Cart.objects.get(session_key=session_key, user__isnull=True)
    except Cart.DoesNotExist:
        return

    # Get or create the user's cart
    user_cart, _ = Cart.objects.get_or_create(user=user)

    with transaction.atomic():
        for item in session_cart.items.all():
            # Try to find the same product in the user cart
            user_item, created = CartItem.objects.get_or_create(
                cart=user_cart, product=item.product,
                defaults={'quantity': item.quantity}
            )
            if not created:
                # If already exists, update the quantity
                user_item.quantity += item.quantity
                user_item.save()

        # Delete session cart and its items
        session_cart.delete()
