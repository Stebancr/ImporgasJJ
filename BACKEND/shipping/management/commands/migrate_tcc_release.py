"""Keep the whole additive release invisible until rollback defaults are installed."""
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.db.migrations.executor import MigrationExecutor


class Command(BaseCommand):
    help = 'Aplicar el plan pendiente en una transacción PostgreSQL para conservar compatibilidad con la versión anterior.'

    def handle(self, *args, **options):
        if connection.vendor != 'postgresql':
            raise CommandError('Este procedimiento requiere PostgreSQL con DDL transaccional.')
        executor = MigrationExecutor(connection)
        plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
        if any(backwards or not migration.atomic for migration, backwards in plan):
            raise CommandError('El plan contiene una reversión o migración no atómica y requiere revisión manual.')
        with transaction.atomic():
            call_command('migrate', interactive=False, stdout=self.stdout, stderr=self.stderr)
