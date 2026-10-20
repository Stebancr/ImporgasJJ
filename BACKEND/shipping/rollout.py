"""Independent quote rollout; disabling it never changes a price to free shipping."""
from django.conf import settings


def enabled_for(user):
    return settings.TCC_SHIPPING_ENABLED and (
        not settings.TCC_ADMIN_ONLY or (getattr(user, 'is_authenticated', False)
                                       and getattr(user, 'tipo_usuario', 0) in (1, 4)))


def missing_fields(profile):
    if profile is None:
        return ['weight_kg', 'height_cm', 'width_cm', 'length_cm', 'packages_per_unit', 'declared_value', 'packaging_code']
    if not profile.requires_shipping:
        return []
    missing = [field for field in ('weight_kg', 'height_cm', 'width_cm', 'length_cm', 'declared_value')
               if getattr(profile, field) is None or getattr(profile, field) <= 0]
    if not profile.packages_per_unit or not 1 <= profile.packages_per_unit <= 100:
        missing.append('packages_per_unit')
    if profile.packaging_code not in ('CLEM_CAJA', 'CLEM_MEDIANA'):
        missing.append('packaging_code')
    return missing
