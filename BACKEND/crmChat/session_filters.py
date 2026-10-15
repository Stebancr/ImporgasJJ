"""One validated filter contract for the inbox and its counters."""
from django.db.models import F, Q
from rest_framework import serializers

from .models import ChannelIntegration, ChatSession


class SessionFilters(serializers.Serializer):
    channel = serializers.ChoiceField(choices=['all'] + [key for key, _ in ChannelIntegration.CHANNEL_CHOICES], required=False)
    status = serializers.ChoiceField(choices=['all'] + [key for key, _ in ChatSession.STATUS_CHOICES], required=False)
    priority = serializers.ChoiceField(choices=['all', 'low', 'normal', 'high', 'urgent'], required=False)
    queue = serializers.IntegerField(min_value=1, required=False)
    search = serializers.CharField(required=False, allow_blank=True, max_length=200)
    unanswered = serializers.BooleanField(required=False)


def filtered_sessions(params):
    filters = SessionFilters(data=params)
    filters.is_valid(raise_exception=True)
    values = filters.validated_data
    qs = ChatSession.objects.all()
    for field in ('channel', 'status', 'priority'):
        if values.get(field) and values[field] != 'all':
            qs = qs.filter(**{field: values[field]})
    if values.get('queue'):
        qs = qs.filter(queue_id=values['queue'])
    if values.get('search'):
        text = values['search']
        qs = qs.filter(Q(user_name__icontains=text) | Q(user_cedula__icontains=text)
                       | Q(external_thread_id__icontains=text) | Q(contact__phone__icontains=text))
    if values.get('unanswered'):
        qs = qs.filter(last_customer_message_at__isnull=False).filter(
            Q(last_agent_message_at__isnull=True) | Q(last_agent_message_at__lt=F('last_customer_message_at')))
    return qs
