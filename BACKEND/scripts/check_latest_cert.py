import os, sys, django, zipfile
os.environ.setdefault('DJANGO_SETTINGS_MODULE','core.settings')
django.setup()
from django.conf import settings

media_root = settings.MEDIA_ROOT
cert_dir = os.path.join(media_root, 'certificados_generados')
print('MEDIA_ROOT:', media_root)
print('SEARCH DIR:', cert_dir)

candidates = []
for root, dirs, files in os.walk(cert_dir):
    for f in files:
        path = os.path.join(root, f)
        try:
            mtime = os.path.getmtime(path)
        except Exception:
            mtime = 0
        size = os.path.getsize(path)
        candidates.append((mtime, path, size))

if not candidates:
    print('No se encontraron archivos en certificados_generados')
    sys.exit(0)

candidates.sort(reverse=True)
mtime, path, size = candidates[0]
print('LATEST FILE:', path)
print('SIZE:', size)
print('MTIME:', mtime)

# print first bytes
with open(path, 'rb') as fh:
    head = fh.read(512)
    print('FIRST BYTES:', head[:64])

# Try as zip (docx)
is_zip = zipfile.is_zipfile(path)
print('is_zipfile:', is_zip)
if is_zip:
    try:
        with zipfile.ZipFile(path, 'r') as z:
            print('ZIP entries sample:', z.namelist()[:20])
    except Exception as e:
        print('Error opening zipfile:', e)
else:
    print('File does not appear to be a zip (not a valid DOCX)')
