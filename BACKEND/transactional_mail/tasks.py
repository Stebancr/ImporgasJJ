from datetime import timedelta
from celery import shared_task
from django.conf import settings
from django.utils import timezone
from django.db.models import Q, F
from .models import Delivery


@shared_task(ignore_result=True)
def deliver(pk):
    from .service import send
    return send(pk)


@shared_task(ignore_result=True)
def recover_pending():
    if not settings.TRANSACTIONAL_EMAIL_ENABLED:
        return
    # SMTP cannot guarantee exactly-once after disconnect/process death. Do not resend blindly.
    Delivery.objects.filter(state='sending',started_at__lt=timezone.now()-timedelta(minutes=5)).update(
        state='uncertain',last_error='worker_interrupted_manual_review')
    for pk in Delivery.objects.filter(state__in=['pending','failed'],attempts__lt=F('max_attempts')).filter(
            Q(next_attempt_at__isnull=True)|Q(next_attempt_at__lte=timezone.now())).values_list('pk',flat=True)[:50]:
        deliver.delay(str(pk))
