"""Customer promotion, separate from the carrier's payable rate.

The policy is frozen in each quote's snapshot. Historical quotes without a
policy retain their original carrier-only charge. No order is backfilled.
"""
from decimal import Decimal
from django.conf import settings
from ecommerce.pricing import totals


def money(value):
    return totals(value)['subtotal']


def threshold():
    value = money(settings.FREE_SHIPPING_THRESHOLD)
    if value <= 0:
        raise ValueError('FREE_SHIPPING_THRESHOLD must be positive')
    return value


def shipping_policy(subtotal, carrier_cost, *, discounts=0, limit=None, requires_shipping=True):
    limit = threshold() if limit is None else money(limit)
    eligible = max(Decimal('0.00'), money(subtotal) - money(discounts))
    carrier = money(carrier_cost)
    applied = bool(requires_shipping and carrier > 0 and eligible >= limit)
    charge = Decimal('0.00') if applied else carrier
    return {'carrier_shipping_cost': str(carrier), 'customer_shipping_charge': str(charge),
            'shipping_discount': str(carrier - charge), 'free_shipping_applied': applied,
            'free_shipping_threshold': str(limit), 'eligible_subtotal': str(eligible),
            'amount_to_free_shipping': str(max(Decimal('0.00'), limit - eligible))}


def order_shipping_fields(policy):
    """Copy only server-frozen accounting fields; never accept browser values."""
    return {key: policy[key] for key in ('carrier_shipping_cost', 'shipping_discount',
            'free_shipping_applied', 'free_shipping_threshold') if key in policy}
