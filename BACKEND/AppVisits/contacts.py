import re

from django.db import IntegrityError, transaction
from django.db.models import Q
from rest_framework import serializers


def normalize_phone(value):
    digits = re.sub(r'[ +().-]', '', value)
    if len(digits) == 12 and digits.startswith('57'):
        return digits[2:]
    if len(digits) == 14 and digits.startswith('0057'):
        return digits[4:]
    return digits


CONTACT_FIELDS = ('nombre', 'identificacion', 'telefono', 'correo', 'direccion', 'indicaciones_llegada')


def save_contact(queryset, values, instance=None):
    phone = normalize_phone(values['telefono'])
    email = values['correo'].strip().lower()
    if not re.fullmatch(r'[0-9]{7,15}', phone):
        raise serializers.ValidationError({'telefono': 'Ingresa un teléfono válido.'})
    matches = queryset.filter(Q(telefono_clave=phone) | Q(correo_clave=email))
    if instance:
        matches = matches.exclude(pk=instance.pk)

    def reject_conflict():
        ids = list(matches.order_by('pk').values_list('pk', flat=True))
        if ids:
            raise serializers.ValidationError({
                'cliente_coincidencias': ids,
                'detail': 'El teléfono o correo coincide con una ficha existente. Revisa las coincidencias.',
            })

    reject_conflict()
    values = {**values, 'telefono': phone, 'correo': email, 'telefono_clave': phone, 'correo_clave': email}
    try:
        with transaction.atomic():
            if not instance:
                return queryset.create(**values)
            for field, value in values.items():
                setattr(instance, field, value)
            instance.save(update_fields=list(values))
            return instance
    except IntegrityError:
        reject_conflict()
        raise
