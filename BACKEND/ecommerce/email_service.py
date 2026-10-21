"""Compatibility entry point; delivery is handled asynchronously by Celery."""
import logging

def send_order_payment_confirmation(order_id):
    from transactional_mail.service import queue
    try:
        return queue('order', order_id)
    except Exception:
        logging.getLogger(__name__).warning('transactional_email event_registration_failed kind=order id=%s', order_id)
        return False