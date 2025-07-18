from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import (
    ListView, DetailView, View, TemplateView
)
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import Q, Min, Max
from django.conf import settings
from django.utils.decorators import method_decorator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.contrib.sites.shortcuts import get_current_site
from .token import *
from django.http import Http404
from django.contrib.auth import logout
from django.utils.crypto import get_random_string
from .utils import *
from django.contrib.auth.views import LoginView


from django.http import HttpResponse, HttpResponseForbidden
from django.core.management import call_command
from django.contrib.auth import get_user_model



try:
    import json
except ImportError:
    import simplejson as json

import requests
from decouple import config
from .models import *
from .forms import *

def generateTransactionPin():
    from random import randint, choice
    from string import ascii_uppercase
    digits = ''.join(str(randint(0, 9)) for _ in range(8))
    return f'{choice(ascii_uppercase)}{digits}{choice(ascii_uppercase)}'


def show_ajax_message(request, message, level='success'):
    getattr(messages, level, messages.info)(request, message)

class CustomLoginView(LoginView):
    template_name = 'accounts/login.html'
    authentication_form = LoginForm

    def form_invalid(self, form):
        username_or_email = form.cleaned_data.get('username')
        try:
            if '@' in username_or_email:
                user = User.objects.get(email=username_or_email)
            else:
                user = User.objects.get(username=username_or_email)
            if not user.is_active:
                messages.error(self.request, "Your account is not active. Please check your email for the activation link or contact support.")
            else:
                messages.error(self.request, "The password you entered is incorrect. Please try again.")

        except User.DoesNotExist:
            messages.error(self.request, "That username or email does not exist. Please check your credentials or create an account.")
        except Exception as e:
            messages.error(self.request, f"An unexpected error occurred: {e}. Please try again.")
        return super().form_invalid(form)

    # def get_success_url(self):
    #     return reverse('home')


def register_view(request):
    form = RegisterForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save(commit=False)
        user.is_active = False
        user.save()

        Customer.objects.create(
            user=user,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name
        )
        current_site = get_current_site(request)
        subject = "Activate Your EStore Account"
        message = render_to_string('accounts/activation_email.html', {
            'user': user,
            'domain': current_site.domain,
            'uid': urlsafe_base64_encode(force_bytes(user.pk)),
            'token': account_activation_token.make_token(user),
            'protocol': 'https' if request.is_secure() else 'http',
        })
        try:
            send_mail(subject, '', settings.DEFAULT_FROM_EMAIL,
                      [user.email], html_message=message)
            messages.success(request, "A confirmation email has been sent to your email address. Please click on the link to activate your account.")
        except Exception as e:
            print(f"SMTP error: {e}")
            messages.error(request,
                           "Could not send verification email. Please contact support.")

        return redirect('login')

    return render(request, 'accounts/register.html', {'form': form})


def customerLogout(request):
    logout(request)
    messages.info(request, "You have been successfully logged out.")
    return redirect('login')

def activate(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user and account_activation_token.check_token(user, token):
        user.is_active = True
        user.save()
        messages.success(request, 'Your account is now active – you can log in.')
        return redirect('login')

    messages.warning(request, 'Activation link is invalid or expired.')
    return redirect('register')

class HomeView(TemplateView):
    template_name = 'index.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['featured_products'] = (
            Product.objects.filter(available=True).order_by('?')[:6]
        )
        return ctx

class ProductListView(ListView):
    model = Product
    template_name = 'products.html'
    context_object_name = 'products'
    paginate_by = 9

    def get_queryset(self):
        qs = Product.objects.filter(available=True)

        q = self.request.GET.get('q')
        cat = self.request.GET.get('category')
        sort = self.request.GET.get('sort_by', 'name')
        min_p = self.request.GET.get('min_price')
        max_p = self.request.GET.get('max_price')

        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(description__icontains=q))
        if cat:
            qs = qs.filter(category__slug=cat)
        if min_p:
            try:
                qs = qs.filter(price__gte=float(min_p))
            except ValueError:
                pass
        if max_p:
            try:
                qs = qs.filter(price__lte=float(max_p))
            except ValueError:
                pass

        ordering_map = {
            'price_asc': 'price',
            'price_desc': '-price',
            'created': '-created',
            'name': 'name',
        }
        qs = qs.order_by(ordering_map.get(sort, 'name'))
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['categories'] = Category.objects.all()

        price_range = self.object_list.aggregate(
            min_price=Min('price'), max_price=Max('price')
        )
        ctx['price_range'] = price_range

        # echo filters back to template
        ctx.update({
            'sort_by': self.request.GET.get('sort_by', 'name'),
            'query': self.request.GET.get('q', ''),
            'min_price_param': self.request.GET.get('min_price', ''),
            'max_price_param': self.request.GET.get('max_price', ''),
            'selected_category': Category.objects.filter(
                slug=self.request.GET.get('category')
            ).first()
        })
        return ctx


class ProductDetailView(DetailView):
    model = Product
    template_name = 'product_details.html'
    context_object_name = 'product'
    slug_url_kwarg = 'slug'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        prod = self.object
        ctx['related_products'] = (
            Product.objects.filter(category=prod.category, available=True)
            .exclude(id=prod.id).order_by('?')[:4]
        )
        ctx['ratings'] = prod.ratings.all()
        return ctx

def cart_view(request):
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
    else:
        if not request.session.session_key:
            request.session.create()
        session_key = request.session.session_key
        cart, _ = Cart.objects.get_or_create(session_key=session_key, user=None)

    items = cart.items.select_related('product')
    subtotal = cart.get_total_cost()
    shipping = settings.SHIPPING_COST if items.exists() else 0
    tax = subtotal * settings.TAX_RATE
    total = subtotal + shipping + tax

    categories = items.values_list('product__category', flat=True).distinct()
    exclude_ids = items.values_list('product__id', flat=True)
    recommended = Product.objects.filter(category__in=categories).exclude(id__in=exclude_ids).distinct()[:6]

    return render(
        request,
        'cart.html',
        {
            'cart': cart,
            'cart_items': items,
            'subtotal': subtotal,
            'shipping': shipping,
            'tax': tax,
            'total': total,
            'recommended_products': recommended,
            'empty_cart': not items.exists(),
        }
    )


@require_POST
def add_to_cart_api(request):
    try:
        data = json.loads(request.body)
        product_id = data.get('product_id')
        quantity_to_add = int(data.get('quantity', 1))
        product = get_object_or_404(Product, id=product_id)

        if product.stock == 0:
            return JsonResponse({
                'success': False,
                'message': f"'{product.name}' is currently out of stock."
            }, status=400)

        # Handle user or session-based cart
        if request.user.is_authenticated:
            cart, created_cart = Cart.objects.get_or_create(user=request.user)
        else:
            session_key = request.session.session_key
            if not session_key:
                request.session.save()
                session_key = request.session.session_key
            cart, created_cart = Cart.objects.get_or_create(session_key=session_key, user=None)

        cart_item, created_item = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={'quantity': 0}
        )

        new_cart_item_qty = cart_item.quantity + quantity_to_add

        if new_cart_item_qty > product.stock:
            return JsonResponse({
                'success': False,
                'message': f"Cannot add {quantity_to_add} more. Only {product.stock - cart_item.quantity} available. Total requested: {new_cart_item_qty}."
            }, status=400)
        
        cart_item.quantity = new_cart_item_qty
        cart_item.save()

        current_cart_total_quantity = cart.get_total_quantity()
        current_cart_total_cost = cart.get_total_cost()

        return JsonResponse({
            'success': True,
            'cart_count': current_cart_total_quantity,
            'cart_total_cost': str(current_cart_total_cost)
        })

    except Product.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Product not found.'
        }, status=404)

    except (json.JSONDecodeError, ValueError, TypeError) as e:
        print(f"Error parsing request body or invalid data: {e}")
        return JsonResponse({
            'success': False,
            'message': f'Invalid request data: {e}'
        }, status=400) 

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return JsonResponse({
            'success': False,
            'message': 'An unexpected error occurred.'
        }, status=500) 

@require_POST
def update_cart_item_api(request):
    try:
        data = json.loads(request.body)
        new_qty = int(data.get('quantity'))
        product_id = data.get('product_id')

        cart = get_or_create_cart(request)
        cart_item = get_object_or_404(CartItem, cart=cart, product_id=product_id)

        if new_qty <= 0:
            cart_item.delete()
        elif new_qty > cart_item.product.stock:
            return JsonResponse({
                'success': False,
                'message': f'Only {cart_item.product.stock} available.'
            }, status=400)
        else:
            cart_item.quantity = new_qty
            cart_item.save()

        return JsonResponse({
            'success': True,
            'cart_count': cart.get_total_quantity(),
            'cart_total_cost': cart.get_total_cost()
        })

    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'success': False, 'message': 'Invalid request.'}, status=400)


@require_POST
def remove_from_cart_api(request):
    try:
        data = json.loads(request.body)
        product_id = data.get('product_id')

        cart = get_or_create_cart(request)
        cart_item = get_object_or_404(CartItem, cart=cart, product_id=product_id)
        cart_item.delete()

        return JsonResponse({
            'success': True,
            'cart_count': cart.get_total_quantity(),
            'cart_total_cost': cart.get_total_cost()
        })

    except (json.JSONDecodeError, CartItem.DoesNotExist):
        return JsonResponse({'success': False, 'message': 'Invalid request.'}, status=400)


@method_decorator(login_required, name='dispatch')
class CheckoutView(View):
    def get(self, request, *args, **kwargs):
        cart = get_object_or_404(Cart, user=request.user)
        if not cart.items.exists():
            messages.warning(request, "Your cart is empty.")
            return redirect('cart')

        # Load default billing address if exists
        initial = {}
        default_addr = BillingAddress.objects.filter(
            user=request.user, is_default=True
        ).first() or BillingAddress.objects.filter(user=request.user).first()

        if default_addr:
            initial = {
                'first_name': default_addr.first_name,
                'last_name': default_addr.last_name,
                'email': default_addr.email,
                'address': default_addr.address,
                'city': default_addr.city,
                'zipcode': default_addr.zipcode,
                'phone': default_addr.phone,
                'country': default_addr.country,
                'order_note': default_addr.order_note,
            }

        form = CheckoutForm(initial=initial)

        subtotal = cart.get_total_cost()
        shipping = settings.SHIPPING_COST if cart.items.exists() else 0
        tax = subtotal * settings.TAX_RATE
        total = subtotal + shipping + tax

        return render(request, 'checkout.html', {
            'form': form,
            'billing_form': form,  # For backward compatibility with template
            'cart': cart,
            'cart_items': cart.items.all(),
            'subtotal': subtotal,
            'shipping': shipping,
            'tax': tax,
            'total': total,
            'paystack_public_key': config('PAYSTACK_PUBLIC_KEY')
        })

    def post(self, request, *args, **kwargs):
        cart = get_object_or_404(Cart, user=request.user)
        form = CheckoutForm(request.POST)

        if not cart.items.exists():
            messages.warning(request, "Your cart is empty.")
            return redirect('cart')

        if form.is_valid():
            BillingAddress.objects.update_or_create(
                user=request.user,
                email=form.cleaned_data['email'],
                defaults={**form.cleaned_data}
            )
            return redirect('payment')

        subtotal = cart.get_total_cost()
        shipping = settings.SHIPPING_COST if cart.items.exists() else 0
        tax = subtotal * settings.TAX_RATE
        total = subtotal + shipping + tax

        return render(request, 'checkout.html', {
            'form': form,
            'billing_form': form,
            'cart': cart,
            'cart_items': cart.items.all(),
            'subtotal': subtotal,
            'shipping': shipping,
            'tax': tax,
            'total': total,
            'paystack_public_key': config('PAYSTACK_PUBLIC_KEY')
        })



def services_view(request):
    return render(request, 'services.html')

class OrderHistoryView(LoginRequiredMixin, ListView):
    model = Order
    template_name = 'order_history.html'
    context_object_name = 'orders'
    paginate_by = 5

    def get_queryset(self):
        qs = Order.objects.filter(user=self.request.user, ordered=True)
        q = self.request.GET.get('q')
        status = self.request.GET.get('status')
        if q:
            qs = qs.filter(id__icontains=q)
        if status:
            qs = qs.filter(status=status)
        return qs.order_by('-ordered_date')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({
            'status_choices': Order.STATUS_CHOICES,
            'current_status_filter': self.request.GET.get('status', ''),
            'current_query': self.request.GET.get('q', ''),
        })
        return ctx


@login_required
def invoice_template_view(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    subtotal = order.get_total_price()
    shipping = settings.SHIPPING_COST if order.order_items.exists() else 0
    tax = subtotal * settings.TAX_RATE
    grand_total = subtotal + shipping + tax

    return render(
        request, 'invoice_template.html',
        {
            'order': order,
            'order_items': order.order_items.all(),
            'subtotal': subtotal,
            'shipping': shipping,
            'tax': tax,
            'grand_total': grand_total,
        }
    )

def success_view(request):
    order_id = request.session.pop('last_order_id', None)
    order = Order.objects.filter(id=order_id, user=request.user).first() if order_id else None

    return render(request, 'success.html', {
        'order': order,
        'order_id_display': order.id if order else 'N/A',
        'order_date_display': order.ordered_date.strftime('%B %d, %Y') if order else 'N/A',
        'order_total_display': f"${order.get_total_price():.2f}" if order else 'N/A',
    })


class PaymentMethodsView(LoginRequiredMixin, TemplateView):
    template_name = 'payment.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        user = self.request.user
        cart = getattr(user, 'cart', None)

        if not cart or not cart.items.exists():
            context['error'] = "Your cart is empty. Please add items to proceed."
            return context

        insufficient_stock = []
        for item in cart.items.select_related('product'):
            if item.product.stock < item.quantity:
                insufficient_stock.append({
                    'product': item.product.name,
                    'available': item.product.stock,
                    'requested': item.quantity
                })

        if insufficient_stock:
            error_msg = "Some items in your cart are no longer available in the requested quantity:<br>"
            for entry in insufficient_stock:
                error_msg += f"<strong>{entry['product']}</strong>: Available: {entry['available']}, You requested: {entry['requested']}<br>"
            context['error'] = error_msg
            return context

        order = Order.objects.create(user=user)
        for item in cart.items.select_related('product'):
            OrderItem.objects.create(
                order=order,
                product=item.product,
                price=item.price_at_addition or item.product.get_display_price(),
                quantity=item.quantity
            )

        bill_address = BillingAddress.objects.filter(user=user).first()
        if bill_address:
            order.billing_address = bill_address
            order.save()

        cart.clear()

        shipping = settings.SHIPPING_COST
        tax = order.get_total_price() * settings.TAX_RATE
        grand_total = order.get_total_price() + shipping + tax

        reference = f"ECOM-{get_random_string(12).upper()}"

        context.update({
            'orders': order,
            'bill_address': bill_address,
            'unique_ref': reference,
            'paystack_public_key': settings.PAYSTACK_PUBLIC_KEY,
            'shipping': shipping,
            'tax': tax,
            'grand_total': grand_total,
        })
        return context

@login_required
def submit_review(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.method == 'POST':
        value = int(request.POST.get('rating', 5))
        comment = request.POST.get('comment', '').strip()

        if comment:
            Rating.objects.update_or_create(
                product=product,
                user=request.user,
                defaults={'value': value, 'comment': comment}
            )

    return redirect('product_detail', slug=product.slug)


@login_required
def verifyPayment(request):
    txref = request.GET.get('reference', '').strip()
    if not txref:
        raise Http404("Missing transaction reference.")
    order = Order.objects.filter(user=request.user, ordered=False).order_by('-id').first()
    if not order:
        raise Http404("No pending order found for verification.")
    
    verify_url = f"https://api.paystack.co/transaction/verify/{txref}"
    headers = {
        'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}'
    }

    try:
        response = requests.get(verify_url, headers=headers)
        data = response.json()
    except Exception as e:
        print(f"[Paystack] Request failed: {e}")
        return redirect('checkout')

    if data.get('status') is True:
        trx_data = data.get('data', {})
        amount_paid = trx_data.get('amount', 0)
        currency = trx_data.get('currency')
        status = trx_data.get('status')

        expected_amount = int((order.get_total_price() + settings.SHIPPING_COST + (order.get_total_price() * settings.TAX_RATE)) * 100)

        if status == 'success' and amount_paid == expected_amount and currency == 'NGN':
            if not Payment.objects.filter(reference=txref).exists():
                card_info = trx_data.get('authorization', {})
                payment = Payment.objects.create(
                    user=request.user,
                    reference=txref,
                    amount=(amount_paid / 100),
                    payment_gateway='PAYSTACK',
                    card_brand=(card_info.get('brand') or 'UNKNOWN').upper(),
                    card_last_four=card_info.get('last4'),
                )

                order.payment = payment
                for item in order.order_items.select_related('product'):
                    product = item.product
                    if product and product.stock >= item.quantity:
                        product.stock -= item.quantity
                        product.save()
                order.ordered = True
                order.save()
                send_order_confirmation_email(order)
            request.session['last_order_id'] = order.id
            return redirect('success')
        else:
            print(f"[Paystack] Invalid payment: status={status}, amount={amount_paid}, currency={currency}")
            return redirect('checkout')
    else:
        print(f"[Paystack] Failed response: {data}")
        return redirect('checkout')
    
def faq_view(request):
    return render(request, 'faq.html', {})

def contact_view(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your message has been sent successfully! We will get back to you soon.')
            return redirect('contact')
        else:
            messages.error(request, 'There was an error with your submission. Please correct the highlighted fields.')
    else:
        form = ContactForm()

    context = {
        'form': form,
        'page_title': 'Contact Us',
    }
    return render(request, 'contact.html', context)
