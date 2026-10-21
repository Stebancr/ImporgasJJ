"""Shared email identity, independent of sender avatars/BIMI and SMTP credentials."""
import ipaddress
import logging
from email.mime.image import MIMEImage
from pathlib import Path
from urllib.parse import urlsplit
from django.conf import settings

logger = logging.getLogger(__name__)
LOGO_PATH = Path(__file__).resolve().parent / 'assets' / 'logo-imporgas.png'
LOGO_CID = 'imporgas-logo'


def logo_context():
    configured = getattr(settings, 'EMAIL_LOGO_URL', '').strip()
    if configured:
        try:
            url = urlsplit(configured)
            allowed = {urlsplit(getattr(settings, key, '')).hostname for key in
                       ('FRONTEND_PUBLIC_URL', 'EXTERNAL_PRODUCT_URL_TEMPLATE')}
        except ValueError:
            # A malformed optional URL must not prevent business mail delivery.
            url = urlsplit('')
            allowed = set()
        host = (url.hostname or '').lower()
        private = host in ('localhost', 'backend', 'frontend', 'nginx') or host.endswith(('.localhost','.local','.internal'))
        try:
            private = private or not ipaddress.ip_address(host).is_global
        except ValueError:
            pass
        if (url.scheme == 'https' and host in allowed and not private and not url.username
                and not url.password and not url.query and not url.fragment):
            return {'email_logo_src':configured, 'email_logo_inline':False}
        logger.warning('email_branding source=inline reason=invalid_EMAIL_LOGO_URL')
    if LOGO_PATH.is_file():
        return {'email_logo_src':'cid:'+LOGO_CID, 'email_logo_inline':True}
    logger.warning('email_branding source=text reason=logo_asset_unavailable')
    return {'email_logo_src':'', 'email_logo_inline':False}


def attach_logo(message, context):
    if not context.get('email_logo_inline'):
        return
    image = MIMEImage(LOGO_PATH.read_bytes(), _subtype='png')
    image.add_header('Content-ID', '<'+LOGO_CID+'>')
    image.add_header('Content-Disposition', 'inline', filename='logo-imporgas.png')
    # Keep regular attachments intact if a caller already supplied any.
    if not message.attachments:
        message.mixed_subtype = 'related'
    message.attach(image)
