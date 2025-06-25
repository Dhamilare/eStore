from django.template.loader import render_to_string
from decouple import config
from django.utils import timezone
import logging
from django.contrib.sites.models import Site
from django.core.mail import send_mail
from django.conf import settings
from django.utils.html import strip_tags
from .models import *

logger = logging.getLogger(__name__)

def send_order_confirmation_email(order):
    subject = f"Order Confirmation – #{order.id}"
    recipient_email = order.billing_address.email if order.billing_address else (order.user.email if order.user else None)

    if not recipient_email:
        logger.warning(f"Could not send order confirmation email for Order #{order.id}: No recipient email found.")
        return

    current_site = Site.objects.get_current()
    domain = current_site.domain
    site_url = f"http://{domain}"

    context = {
    "order": order,
    "customer": order.user,
    "current_year": timezone.now().year,
    "site_name": current_site.name,
    "domain": domain,
    "site_url": site_url,
}

    html_body = render_to_string("emails/order_confirmation.html", context)
    plain_text_body = strip_tags(html_body)

    try:
        send_mail(
            subject=subject,
            message=plain_text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient_email],
            html_message=html_body,
            fail_silently=False,
        )
        logger.info(f"Order confirmation email sent for Order #{order.id} to {recipient_email}")
    except Exception as e:
        logger.error(f"Failed to send order confirmation email for Order #{order.id} to {recipient_email}: {e}")


def send_order_status_update_email(order, new_status):
    subject = f"Your eStore Order #{order.id} is now {new_status}"
    recipient_email = order.billing_address.email if order.billing_address else (order.user.email if order.user else None)

    if not recipient_email:
        logger.warning(f"Could not send order status update email for Order #{order.id}: No recipient email found.")
        return

    current_site = Site.objects.get_current()

    context = {
        "order": order,
        "customer": order.user,
        "status": new_status,
        "current_year": timezone.now().year,
        "site_name": current_site.name,
        "domain": current_site.domain,
    }

    html_body = render_to_string("emails/order_status_update.html", context)
    plain_text_body = strip_tags(html_body)

    try:
        send_mail(
            subject=subject,
            message=plain_text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient_email],
            html_message=html_body,
            fail_silently=False,
        )
        logger.info(f"Order status update email sent for Order #{order.id} (Status: {new_status}) to {recipient_email}")
    except Exception as e:
        logger.error(f"Failed to send order status update email for Order #{order.id} (Status: {new_status}) to {recipient_email}: {e}")


def get_or_create_cart(request):
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
    else:
        # Ensure session exists
        if not request.session.session_key:
            request.session.create()

        session_key = request.session.session_key
        cart, _ = Cart.objects.get_or_create(session_key=session_key)
    return cart