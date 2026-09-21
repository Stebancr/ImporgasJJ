"""Validación compartida para adjuntos cargados por CRM y clientes móviles."""

from pathlib import Path

from django.conf import settings


ALLOWED_ATTACHMENT_TYPES = {
    '.jpg': {'image/jpeg'},
    '.jpeg': {'image/jpeg'},
    '.png': {'image/png'},
    '.webp': {'image/webp'},
    '.gif': {'image/gif'},
    '.pdf': {'application/pdf'},
    '.doc': {'application/msword', 'application/octet-stream'},
    '.docx': {'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'application/zip'},
    '.xls': {'application/vnd.ms-excel', 'application/octet-stream'},
    '.xlsx': {'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'application/zip'},
}


def _signature_matches(extension, header):
    if extension in {'.jpg', '.jpeg'}:
        return header.startswith(b'\xff\xd8\xff')
    if extension == '.png':
        return header.startswith(b'\x89PNG\r\n\x1a\n')
    if extension == '.webp':
        return header.startswith(b'RIFF') and header[8:12] == b'WEBP'
    if extension == '.gif':
        return header.startswith((b'GIF87a', b'GIF89a'))
    if extension == '.pdf':
        return header.startswith(b'%PDF-')
    if extension in {'.doc', '.xls'}:
        return header.startswith(b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1')
    if extension in {'.docx', '.xlsx'}:
        return header.startswith(b'PK\x03\x04')
    return False


def validate_chat_upload(upload):
    """Devuelve nombre, MIME y tipo normalizado o lanza ``ValueError``."""

    maximum = getattr(settings, 'CRM_ATTACHMENT_MAX_BYTES', 25 * 1024 * 1024)
    if upload.size <= 0 or upload.size > maximum:
        raise ValueError(f'El archivo debe pesar entre 1 byte y {maximum} bytes.')
    original_name = Path(upload.name or '').name
    extension = Path(original_name).suffix.lower()
    allowed_mimes = ALLOWED_ATTACHMENT_TYPES.get(extension)
    mime_type = (upload.content_type or '').split(';')[0].strip().lower()
    if not original_name or not allowed_mimes or mime_type not in allowed_mimes:
        raise ValueError('El tipo de archivo no está permitido.')
    header = upload.read(16)
    upload.seek(0)
    if not _signature_matches(extension, header):
        raise ValueError('El contenido del archivo no coincide con su extensión.')
    return original_name[:255], mime_type, 'image' if mime_type.startswith('image/') else 'document'
