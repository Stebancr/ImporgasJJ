from celery import shared_task


@shared_task(ignore_result=True)
def deliver_password_reset(delivery_id):
    from .password_recovery import deliver
    return deliver(delivery_id)
