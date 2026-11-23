"""Persistent revocation metadata. Never store bearer credentials here."""
import uuid
from django.conf import settings
from django.db import models


class GlobalAuthState(models.Model):
    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    version = models.PositiveBigIntegerField(default=1)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(id=1), name='single_global_auth_state')]


class AuthSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    global_auth_version = models.PositiveBigIntegerField()
    password_version = models.PositiveIntegerField()
    issued_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)
    credential_type = models.CharField(max_length=20, default='jwt')


class PersistentTokenVersion(models.Model):
    token = models.OneToOneField('authtoken.Token', on_delete=models.CASCADE, primary_key=True)
    global_auth_version = models.PositiveBigIntegerField()
    password_version = models.PositiveIntegerField()
    issued_at = models.DateTimeField(auto_now_add=True)
    session = models.OneToOneField(AuthSession, on_delete=models.CASCADE)


class AuthRevocation(models.Model):
    operation_id = models.CharField(primary_key=True, max_length=80)
    version = models.PositiveBigIntegerField()
    reason = models.CharField(max_length=80)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    executor_label = models.CharField(max_length=40, default='')
    executed_at = models.DateTimeField(auto_now_add=True)
    django_sessions = models.PositiveIntegerField(default=0)
    refresh_sessions = models.PositiveIntegerField(default=0)
    drf_tokens = models.PositiveIntegerField(default=0)
