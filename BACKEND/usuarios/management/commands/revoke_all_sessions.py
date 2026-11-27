import json
import re
import uuid
import os
from django.contrib.sessions.models import Session
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from django.conf import settings
from rest_framework.authtoken.models import Token
from usuarios.models import GlobalAuthState, AuthSession, AuthRevocation, Credenciales


class Command(BaseCommand):
    help = 'Invalidate all credentials without changing users. Reuse operation-id for an idempotent retry.'

    def add_arguments(self, parser):
        parser.add_argument('--reason', required=True)
        parser.add_argument('--operation-id', default=None)
        parser.add_argument('--actor-id', type=int)
        parser.add_argument('--system-actor', choices=['deployment-root'])

    def handle(self, *args, **options):
        reason = options['reason']
        operation = options['operation_id'] or str(uuid.uuid4())
        if not re.fullmatch(r'[a-zA-Z0-9_.:-]{1,80}', reason) or not re.fullmatch(r'[a-zA-Z0-9_.:-]{1,80}', operation):
            raise CommandError('Reason and operation-id must be safe codes, not personal data.')
        actor = None
        executor = 'development_cli'
        if options['system_actor'] and options['actor_id']:
            raise CommandError('Choose one administrative identity.')
        if options['system_actor']:
            if not hasattr(os, 'geteuid') or os.geteuid() != 0:
                raise CommandError('deployment-root requires an operating-system root process.')
            executor = 'os:root'
        if not settings.DEBUG and not options['actor_id'] and not options['system_actor']:
            raise CommandError('Production requires an application administrator or explicit root deployment identity.')
        if options['actor_id']:
            actor = Credenciales.objects.filter(pk=options['actor_id'], estado=1, tipo_usuario__in=(1, 4)).first()
            if not actor:
                raise CommandError('Administrative actor not valid.')
            executor = 'application_admin'
        with transaction.atomic():
            GlobalAuthState.objects.get_or_create(pk=1)
            state = GlobalAuthState.objects.select_for_update().get(pk=1)
            event = AuthRevocation.objects.filter(pk=operation).first()
            if event and (event.reason != reason or event.actor_id != (actor.pk if actor else None) or event.executor_label != executor):
                raise CommandError('Operation-id already used with different parameters.')
            if not event:
                state.version += 1
                state.save(update_fields=['version', 'updated_at'])
                event = AuthRevocation.objects.create(operation_id=operation, version=state.version,
                    reason=reason, actor=actor, executor_label=executor, django_sessions=Session.objects.count(),
                    refresh_sessions=AuthSession.objects.filter(revoked_at__isnull=True, credential_type='jwt').count(), drf_tokens=Token.objects.count())
                AuthSession.objects.filter(revoked_at__isnull=True).update(revoked_at=timezone.now())
                Token.objects.all().delete()
                Session.objects.all().delete()
        self.stdout.write(json.dumps({'result': 'ok', 'global_auth_version': event.version,
            'sessions_invalidated': event.django_sessions, 'refresh_tokens_revoked': event.refresh_sessions,
            'drf_tokens_revoked': event.drf_tokens}))
