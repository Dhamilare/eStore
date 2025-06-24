from django.template.loader import render_to_string
import requests
from decouple import config
from datetime import datetime
from django.utils import timezone
import logging
from django.contrib.sites.models import Site
from django.core.mail import send_mail
from django.conf import settings
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)

DHL_BASE_URL = config("DHL_BASE_URL")
DHL_API_KEY = config("DHL_API_KEY")

# Shipper details from settings/env
SHIPPER_POSTAL_CODE = config("SHIPPER_POSTAL_CODE")
SHIPPER_CITY = config("SHIPPER_CITY")
SHIPPER_COUNTRY = config("SHIPPER_COUNTRY")
SHIPPER_EMAIL = config("SHIPPER_EMAIL")
SHIPPER_PHONE = config("SHIPPER_PHONE")


def send_order_confirmation_email(order):
    """
    Sends an order confirmation email to the customer.
    Requires 'my_ecommerce_app/emails/order_confirmation.html' template.
    """
    subject = f"Order Confirmation – #{order.id}"
    # Use order.billing_address.email as the primary recipient
    recipient_email = order.billing_address.email if order.billing_address else (order.user.email if order.user else None)

    if not recipient_email:
        logger.warning(f"Could not send order confirmation email for Order #{order.id}: No recipient email found.")
        return

    current_site = Site.objects.get_current()
    
    # Example for invoice URL (uncomment and configure if you have a 'download_invoice' URL)
    # invoice_url = f"https://{current_site.domain}{reverse('invoice', args=[order.id])}"

    context = {
        "order": order,
        "customer": order.user, # The User object
        "current_year": timezone.now().year,
        "site_name": current_site.name,
        "domain": current_site.domain,
        # "invoice_url": invoice_url, # Uncomment if you enable the invoice_url
    }

    html_body = render_to_string("my_ecommerce_app/emails/order_confirmation.html", context)
    plain_text_body = strip_tags(html_body) # Fallback for plain-text email clients

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
    """
    Sends an email notification when an order's status changes.
    Requires 'my_ecommerce_app/emails/order_status_update.html' template.
    """
    subject = f"Your EcomStore Order #{order.id} is now {new_status}"
    recipient_email = order.billing_address.email if order.billing_address else (order.user.email if order.user else None)

    if not recipient_email:
        logger.warning(f"Could not send order status update email for Order #{order.id}: No recipient email found.")
        return

    current_site = Site.objects.get_current()

    context = {
        "order": order,
        "customer": order.user, # The User object
        "status": new_status,
        "current_year": timezone.now().year,
        "site_name": current_site.name,
        "domain": current_site.domain,
    }

    html_body = render_to_string("my_ecommerce_app/emails/order_status_update.html", context)
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


def create_dhl_shipment(order):
    """
    Creates a DHL shipment request and returns the tracking number.
    This function is called by the Order model's save method.
    It expects DHL API key and base URL to be configured via `decouple`.
    """
    if not DHL_API_KEY or not DHL_BASE_URL:
        logger.error("DHL API key or Base URL is not configured. Cannot create DHL shipment.")
        raise ValueError("DHL API credentials are not set.")

    if not order.billing_address:
        logger.error(f"Order #{order.id} has no billing address. Cannot create DHL shipment.")
        raise ValueError("Billing address is required to create DHL shipment.")

    planned_date = datetime.now(timezone.utc).isoformat()
    
    headers = {
        "DHL-API-Key": DHL_API_KEY,
        "Content-Type": "application/json"
    }

    payload = {
        "plannedShippingDateAndTime": planned_date,
        "pickup": {"isRequested": False}, # Assuming no pickup requested
        "productCode": "P", # Example product code, adjust as needed (e.g., 'D' for Express)
        "customerDetails": {
            "shipperDetails": {
                "postalAddress": {
                    "postalCode": SHIPPER_POSTAL_CODE,
                    "cityName": SHIPPER_CITY,
                    "countryCode": SHIPPER_COUNTRY
                },
                "contactInformation": {
                    "email": SHIPPER_EMAIL,
                    "phone": SHIPPER_PHONE
                }
            },
            "receiverDetails": {
                "postalAddress": {
                    "postalCode": order.billing_address.zipcode,
                    "cityName": order.billing_address.city,
                    "countryCode": str(order.billing_address.country) # Convert CountryField to string code
                },
                "contactInformation": {
                    "email": order.billing_address.email,
                    # Ensure phone number is in a format DHL API expects (e.g., E.164)
                    "phone": str(order.billing_address.phone) if order.billing_address.phone else ""
                }
            }
        },
        "content": {
            "packages": [{
                "weight": {
                    "value": 1.0,  # Default value, consider calculating based on order items
                    "unitOfMeasurement": "KG"
                }
            }],
            "isCustomsDeclarable": False, # Adjust if shipping internationally and requires customs
            "description": f"Order #{order.id} from eCommerce Store" # Dynamic description
        }
    }

    try:
        response = requests.post(DHL_BASE_URL, headers=headers, json=payload)
        response.raise_for_status() # Raises HTTPError for bad responses (4xx or 5xx)
        response_data = response.json()
        
        # DHL API usually returns 'shipmentTrackingNumber' directly at the top level
        tracking_number = response_data.get("shipmentTrackingNumber")
        if not tracking_number:
            raise ValueError(f"DHL API response missing 'shipmentTrackingNumber': {response_data}")

        logger.info(f"DHL shipment created for Order #{order.id}. Tracking: {tracking_number}")
        # Return a dictionary with 'trackingNumber' key to match models.py expectation
        return {'trackingNumber': tracking_number}

    except requests.exceptions.RequestException as e:
        logger.error(f"DHL shipment creation failed for Order #{order.id} (Network/API issue): {e}. Response: {response.text if 'response' in locals() else 'N/A'}")
        raise
    except Exception as e:
        logger.error(f"DHL shipment creation failed for Order #{order.id} (Unexpected error): {e}")
        raise


def fetch_dhl_tracking_info(tracking_number):
    """
    Fetches live tracking information for a DHL shipment.
    This function is called by the DHLTrackingView.
    """
    if not DHL_API_KEY:
        logger.warning("DHL API key not configured. Cannot fetch live tracking info.")
        return None

    # Note: The tracking API endpoint is usually separate from the shipment creation endpoint
    TRACKING_API_URL = "https://api-eu.dhl.com/track/shipments"

    url = f"{TRACKING_API_URL}?trackingNumber={tracking_number}"
    headers = {
        "DHL-API-Key": DHL_API_KEY,
        "Accept": "application/json"
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        data = response.json()

        if data and 'shipments' in data and len(data['shipments']) > 0:
            shipment = data['shipments'][0]

            tracking_info = {
                "status": shipment.get("status", {}).get("status"),
                "last_location": shipment.get("status", {}).get("location", {}).get("address", {}).get("addressLocality"),
                "estimated_delivery": shipment.get("estimatedTimeOfDelivery"),
                "carrier": "DHL", # Hardcode or derive from API response
                "tracking_number": tracking_number,
                "history": [
                    {
                        "date": event.get("timestamp"),
                        "description": event.get("status", {}).get("status"), # Use .get for robustness
                        "location": event.get("location", {}).get("address", {}).get("addressLocality", "Unknown")
                    }
                    for event in shipment.get("events", [])
                ]
            }
            logger.info(f"Successfully fetched DHL tracking info for {tracking_number}")
            return tracking_info
        else:
            logger.info(f"No detailed shipment data found for tracking number: {tracking_number}")
            return None # No shipment data found

    except requests.exceptions.RequestException as e:
        logger.error(f"[DHL Tracking Error - Network/API] {tracking_number}: {e}. Response: {response.text if 'response' in locals() else 'N/A'}")
        return None
    except (KeyError, IndexError, TypeError) as e:
        logger.error(f"[DHL Tracking Error - Parsing] {tracking_number}: {e}. Response data might be malformed: {data if 'data' in locals() else 'N/A'}")
        return None
    except Exception as e:
        logger.error(f"[DHL Tracking Error - Unexpected] {tracking_number}: {e}")
        return None

