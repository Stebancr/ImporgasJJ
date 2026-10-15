"""Server-side monetary breakdown; browser totals are never inputs to pricing."""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


def totals(subtotal, shipping, *, taxes=0, discounts=0):
    values = {}
    for key, value in (('subtotal', subtotal), ('shipping_cost', shipping), ('taxes', taxes), ('discounts', discounts)):
        try:
            number = Decimal(str(value))
            if not number.is_finite() or number < 0:
                raise ValueError()
            values[key] = number.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        except (InvalidOperation, ValueError, TypeError):
            raise ValueError('El desglose monetario no es válido.') from None
    values['total'] = values['subtotal'] + values['shipping_cost'] + values['taxes'] - values['discounts']
    if values['total'] < 0:
        raise ValueError('El descuento no puede superar el importe de la compra.')
    return values


def valid_breakdown(record):
    try:
        return record.total == totals(record.subtotal, record.shipping_cost, taxes=record.taxes, discounts=record.discounts)['total']
    except ValueError:
        return False
