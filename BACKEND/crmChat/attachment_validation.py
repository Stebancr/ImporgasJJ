"""Validate uploads before persistence; never trust browser MIME alone."""
import hashlib
import json
import re
import subprocess
import tempfile
import zipfile
from xml.etree import ElementTree
from pathlib import Path
from django.conf import settings
from PIL import Image
from pypdf import PdfReader

ALLOWED_ATTACHMENT_TYPES = {
    '.jpg': {'image/jpeg'}, '.jpeg': {'image/jpeg'}, '.png': {'image/png'},
    '.webp': {'image/webp'}, '.gif': {'image/gif'}, '.pdf': {'application/pdf'},
    '.docx': {'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'application/zip'},
    '.xlsx': {'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'application/zip'},
    '.mp3': {'audio/mpeg'}, '.ogg': {'audio/ogg', 'application/ogg'},
    '.wav': {'audio/wav', 'audio/x-wav'}, '.m4a': {'audio/mp4', 'audio/x-m4a'},
    '.mp4': {'video/mp4'}, '.webm': {'video/webm'},
}
CHANNEL_MEDIA = {
    'ecommerce': {'image', 'audio', 'video', 'document'},
    'whatsapp_web': {'image', 'audio', 'video', 'document'},
    'facebook': {'image', 'audio', 'video', 'document'},
    'instagram': {'image'},  # Verified endpoint common to both login modes.
    'whatsapp': set(),  # No new Cloud API functionality under zero-cost policy.
}


def ensure_channel_media(channel, kind):
    if kind not in CHANNEL_MEDIA.get(channel, set()):
        raise ValueError('Este canal no tiene habilitado ese tipo de archivo. Usa un canal compatible autorizado.')


def upload_sha256(upload):
    digest = hashlib.sha256()
    upload.seek(0)
    for chunk in upload.chunks():
        digest.update(chunk)
    upload.seek(0)
    return digest.hexdigest()


def validate_chat_upload(upload):
    maximum = getattr(settings, 'CRM_ATTACHMENT_MAX_BYTES', 25 * 1024 * 1024)
    if upload.size <= 0 or upload.size > maximum:
        raise ValueError(f'El archivo debe pesar entre 1 byte y {maximum} bytes.')
    name = Path((upload.name or '').replace('\\', '/')).name
    name = re.sub(r'[^\w. ()-]', '_', name)[:180]
    extension = Path(name).suffix.lower()
    mime = (upload.content_type or '').split(';')[0].strip().lower()
    if not name or mime not in ALLOWED_ATTACHMENT_TYPES.get(extension, set()):
        raise ValueError('Tipo no permitido. Usa imágenes, PDF, DOCX/XLSX sin macros o audio/video compatible.')
    kind = 'document'
    try:
        upload.seek(0)
        if mime.startswith('image/'):
            kind = 'image'
            image = Image.open(upload)
            if image.width * image.height > 25_000_000:
                raise ValueError('La imagen supera el límite de píxeles.')
            expected = {'.jpg': 'JPEG', '.jpeg': 'JPEG', '.png': 'PNG', '.gif': 'GIF', '.webp': 'WEBP'}
            if image.format != expected[extension]:
                raise ValueError('El contenido no coincide con la extensión.')
            image.verify()
        elif extension == '.pdf':
            reader = PdfReader(upload, strict=True)
            if reader.is_encrypted or not reader.pages:
                raise ValueError('No se permiten PDF cifrados o vacíos.')
            dangerous = {'/JS', '/JavaScript', '/AA', '/OpenAction', '/EmbeddedFiles', '/RichMedia', '/Launch', '/XFA'}
            seen = set()
            def inspect(value, depth=0):
                if depth > 80:
                    raise ValueError('PDF demasiado complejo.')
                if hasattr(value, 'get_object'):
                    value = value.get_object()
                if id(value) in seen:
                    return
                seen.add(id(value))
                if isinstance(value, dict):
                    if dangerous.intersection(value) or str(value.get('/S', '')) in dangerous:
                        raise ValueError('No se permite contenido activo en PDF.')
                    for child in value.values():
                        inspect(child, depth + 1)
                elif isinstance(value, (list, tuple)):
                    for child in value:
                        inspect(child, depth + 1)
            inspect(reader.trailer)
        elif extension in {'.docx', '.xlsx'}:
            with zipfile.ZipFile(upload) as archive:
                entries = archive.infolist()
                if len(entries) > 3000 or sum(item.file_size for item in entries) > 80 * 1024 * 1024:
                    raise ValueError('Documento comprimido demasiado grande.')
                prefix = 'word/' if extension == '.docx' else 'xl/'
                if '[Content_Types].xml' not in archive.namelist() or not any(x.filename.startswith(prefix) for x in entries):
                    raise ValueError('El documento no corresponde al formato indicado.')
                for item in entries:
                    lower = item.filename.lower()
                    if '..' in Path(lower).parts or lower.startswith('/') or any(x in lower for x in ('vbaproject', 'embeddings/', 'activex/')):
                        raise ValueError('Documento con contenido activo no permitido.')
                    if lower.endswith(('.rels', '.xml')):
                        root = ElementTree.fromstring(archive.read(item))
                        for element in root.iter():
                            tag = element.tag.rsplit('}', 1)[-1]
                            if any(k.lower() == 'targetmode' and str(v).lower() == 'external' for k, v in element.attrib.items()):
                                raise ValueError('Documento con relaciones externas no permitido.')
                            if (extension == '.xlsx' and tag == 'f') or (extension == '.docx' and tag in ('instrText', 'fldSimple')):
                                raise ValueError('Documento con fórmulas o campos activos no permitido. Adjunta una versión PDF segura.')
        else:
            kind = 'video' if mime.startswith('video/') else 'audio'
            with tempfile.NamedTemporaryFile(suffix=extension) as temp:
                for chunk in upload.chunks():
                    temp.write(chunk)
                temp.flush()
                probe = subprocess.run(['ffprobe', '-v', 'error', '-protocol_whitelist', 'file',
                                        '-show_streams', '-show_format', '-of', 'json', temp.name],
                                       capture_output=True, timeout=8, check=True)
                result = json.loads(probe.stdout)
                streams = result.get('streams', [])
                container = result.get('format', {}).get('format_name', '').split(',')
                expected = {'.mp3': 'mp3', '.ogg': 'ogg', '.wav': 'wav', '.m4a': 'mp4', '.mp4': 'mp4', '.webm': 'webm'}
                if expected[extension] not in container:
                    raise ValueError('El contenedor de audio/video no coincide con su extensión.')
                if not any(s.get('codec_type') == kind for s in streams):
                    raise ValueError('El archivo no contiene audio/video válido.')
                if kind == 'audio' and extension == '.ogg':
                    mime = 'audio/ogg'
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError('Archivo dañado, no verificable o contenido distinto a su extensión.') from exc
    finally:
        upload.seek(0)
    return name, mime, kind
