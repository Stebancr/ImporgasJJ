import os, sys, django, zipfile, time

sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

django.setup()
from django.conf import settings

p = os.path.join(settings.MEDIA_ROOT, 'certificados_generados')

files = [os.path.join(root, f) for root, dirs, fs in os.walk(p) for f in fs]
if not files:
    print('NO_FILES')
    sys.exit(0)

latest = max(files, key=os.path.getmtime)
print('LATEST:', latest)
print('SIZE:', os.path.getsize(latest))
with open(latest, 'rb') as fh:
    h = fh.read(32)
    print('HEAD_BYTES:', h)
    print('IS_PDF:', h.startswith(b'%PDF'))
    print('IS_ZIP:', zipfile.is_zipfile(latest))
print('EXT:', os.path.splitext(latest)[1])
print('MTIME:', time.ctime(os.path.getmtime(latest)))

# Try to print first few textual bytes (safe)
try:
    with open(latest, 'rb') as fh:
        sample = fh.read(1024)
        print('\nSAMPLE (first 1k bytes):')
        print(sample[:200])
except Exception as e:
    print('Error reading sample:', e)
