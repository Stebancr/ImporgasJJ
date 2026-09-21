import re


USER_JID_RE = re.compile(r'^(?P<identifier>\d{8,30})(?::\d+)?@(?P<server>s\.whatsapp\.net|lid)$')


def normalize_user_jid(value):
    """Devuelve un JID directo estable y elimina el sufijo multidispositivo."""

    raw = str(value or '').strip().lower()
    match = USER_JID_RE.fullmatch(raw)
    if not match:
        return ''
    identifier = match.group('identifier')
    server = match.group('server')
    if server == 's.whatsapp.net' and len(identifier) > 15:
        return ''
    return f'{identifier}@{server}'


def external_message_key(connection_id, message_id):
    connection = str(connection_id or '').strip()
    external_id = str(message_id or '').strip()
    if not connection or not external_id:
        return ''
    return f'ww:{connection}:{external_id}'[:255]


def mask_jid(value):
    normalized = normalize_user_jid(value)
    if not normalized:
        return 'invalid'
    identifier, server = normalized.split('@', 1)
    return f'***{identifier[-4:]}@{server}'
