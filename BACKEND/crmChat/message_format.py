"""Safe, deliberately small message grammar shared by all outbound adapters.

Internal: **bold**, _italic_, ~strike~, `code`, lists and HTTP(S) links.
Legacy WhatsApp *bold* is accepted. No HTML is sent to a provider.
"""
import html
import re

TEXT_LIMITS = {'ecommerce': 10000, 'whatsapp_web': 4000, 'whatsapp': 4000, 'facebook': 2000, 'instagram': 1000}
TOKEN = re.compile(r'https?://[^\s<>]+|```[\s\S]+?```|`[^`\n]+`|\*\*[^*\n]+?\*\*|(?<!\w)\*[^*\n]+?\*(?!\w)|(?<!\w)_[^_\n]+?_(?!\w)|(?<!\w)~[^~\n]+?~(?!\w)')


def clean_text(text):
    text = str(text or '').replace('\r\n', '\n').replace('\\n', '\n').replace('http\\://', 'http://').replace('https\\://', 'https://')
    text = re.sub(r'<(script|style)\b[^>]*>[\s\S]*?</\1\s*>', '', text, flags=re.I)
    text = re.sub(r'<br\s*/?>|</(?:p|div|li)>', '\n', text, flags=re.I)
    text = re.sub(r'</?(?:strong|b)\b[^>]*>', '**', text, flags=re.I)
    text = re.sub(r'</?(?:em|i)\b[^>]*>', '_', text, flags=re.I)
    text = html.unescape(re.sub(r'<[^>]*>', '', text))
    # HTML entities must not become a second executable/visible HTML layer.
    text = re.sub(r'<[^>]*>', '', text)
    text = re.sub(r'\[([^\]\n]+)\]\((https?://[^\s)]+)\)', r'\1 (\2)', text)
    return text.strip()


def format_for_channel(text, channel):
    text = clean_text(text)
    def convert(match):
        token = match[0]
        if token.startswith(('http://', 'https://')):
            return token
        n = 3 if token.startswith('```') else 2 if token.startswith('**') else 1
        inner = token[n:-n]
        if channel in ('facebook', 'instagram'):
            return TOKEN.sub(convert, inner)
        if token.startswith('**') and channel in ('whatsapp_web', 'whatsapp'):
            return '*' + inner + '*'
        if token.startswith('*') and not token.startswith('**') and channel == 'ecommerce':
            return '**' + inner + '**'
        return token
    return TOKEN.sub(convert, text)


def validate_message_text(text, channel):
    result = format_for_channel(text, channel)
    if len(result) > TEXT_LIMITS.get(channel, 4000):
        raise ValueError(f'El mensaje supera el límite de {TEXT_LIMITS.get(channel, 4000)} caracteres de este canal. Divide el texto antes de enviar.')
    if '{{' in result or '}}' in result:
        raise ValueError('Completa las variables antes de enviar.')
    return result
