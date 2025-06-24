from .models import Cart

def cart_item_count(request):
    count = 0
    if request.user.is_authenticated:
        try:
            cart = Cart.objects.get(user=request.user)
            count = cart.get_total_quantity()
        except Cart.DoesNotExist:
            pass
    return {'cart_count': count}
