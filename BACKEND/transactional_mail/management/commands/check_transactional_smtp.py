import smtplib
import ssl
from email.utils import parseaddr
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ImproperlyConfigured
from transactional_mail.configuration import validate_smtp, sender_for


class Command(BaseCommand):
    help='Validate SMTP/TLS/authentication without sending a message or printing credentials.'
    def add_arguments(self,parser):
        parser.add_argument('--technical-visits',action='store_true',help='Probe the visit sender envelope only; never sends DATA.')
        parser.add_argument('--password-reset',action='store_true',help='Probe SERVER_EMAIL_NOREPLY only; never sends DATA.')

    def handle(self,*args,**options):
        try:
            validate_smtp()
            if options['password_reset']:
                from usuarios.password_recovery import sender as reset_sender
                sender = reset_sender()
            else:
                sender=sender_for('visit' if options['technical_visits'] else 'order')
            self.stdout.write('Configuration types/TLS: OK')
            with smtplib.SMTP(settings.EMAIL_HOST,settings.EMAIL_PORT,timeout=settings.EMAIL_TIMEOUT) as smtp:
                smtp.ehlo();smtp.starttls(context=ssl.create_default_context());smtp.ehlo()
                self.stdout.write('Connection STARTTLS certificate: OK')
                smtp.login(settings.EMAIL_HOST_USER,settings.EMAIL_HOST_PASSWORD)
                self.stdout.write('Authentication: OK')
                code,_=smtp.mail(parseaddr(sender)[1])
                self.stdout.write('MAIL FROM: '+str(code)+' (not proof of sender verification or delivery)')
                smtp.rset()
        except ImproperlyConfigured as exc:
            raise CommandError(str(exc)) from None
        except ssl.SSLCertVerificationError as exc:
            raise CommandError('TLS certificate verification failed: '+str(exc.verify_code)+' '+exc.verify_message) from None
        except smtplib.SMTPAuthenticationError:
            raise CommandError('SMTP authentication rejected. Verify SMTP login and SMTP key in Brevo; values withheld.') from None
        except Exception as exc:
            raise CommandError('SMTP validation failed: '+type(exc).__name__+'; no credentials or provider reply logged.') from None
