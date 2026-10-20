"""Server-side monetary breakdown; browser totals are never inputs to pricing."""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


def totals(subtotal, *, taxes=0, discounts=0):
    values = {}
    for key, value in (('subtotal', subtotal), ('taxes', taxes), ('discounts', discounts)):
        try:
            number = Decimal(str(value))
            if not number.is_finite() or number < 0:
                raise ValueError()
            values[key] = number.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        except (InvalidOperation, ValueError, TypeError):
            raise ValueError('El desglose monetario no es válido.') from None
    values['shipping_cost'] = None  # Delivery is outside this purchase; never interpreted as free.
    values['total'] = values['subtotal'] + values['taxes'] - values['discounts']
    if values['total'] < 0:
        raise ValueError('El descuento no puede superar el importe de la compra.')
    return values


def valid_breakdown(record):
    try:
        expected = totals(record.subtotal, taxes=record.taxes, discounts=record.discounts)['total']
        # Preserve the exact frozen amount of pre-existing payment intents only.
        # New intents always store NULL and never include a delivery charge.
        if record.shipping_cost is not None:
            historical = Decimal(str(record.shipping_cost))
            if not historical.is_finite() or historical < 0:
                return False
            expected += historical
        return record.total == expected
    except ValueError:
        return False
