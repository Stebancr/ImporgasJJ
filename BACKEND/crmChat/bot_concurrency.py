"""Cross-process leases independent of evictable cache keys."""
import uuid
from contextlib import contextmanager
from datetime import timedelta
from django.db import transaction
from django.utils import timezone
from .models import BotConversationLease, ChatSession


class ConversationBusy(Exception):
    pass


@contextmanager
def conversation_lease(session_id):
    owner = str(uuid.uuid4())
    with transaction.atomic():
        ChatSession.objects.select_for_update().get(pk=session_id)
        lease = BotConversationLease.objects.filter(session_id=session_id).first()
        if lease and lease.expires_at > timezone.now():
            raise ConversationBusy()
        BotConversationLease.objects.update_or_create(session_id=session_id, defaults={
            'owner': owner, 'expires_at': timezone.now() + timedelta(seconds=150),
        })
    try:
        yield owner
    finally:
        BotConversationLease.objects.filter(session_id=session_id, owner=owner).delete()
