"""Reproduce email PNG and a raster-free BIMI derivative of the supplied SVG.

Run only in the Docker artwork tool image (librsvg, potrace, Pillow).
The original SVG is read-only and is never rewritten.
"""
import argparse
import copy
import hashlib
import json
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from PIL import Image

NS = 'http://www.w3.org/2000/svg'
ET.register_namespace('', NS)
COLORS = [(0, 20, 117), (245, 133, 52)]


def build(source, frontend, backend, evidence):
    source, frontend, backend, evidence = map(Path, (source, frontend, backend, evidence))
    for folder in (frontend, backend, evidence):
        folder.mkdir(parents=True, exist_ok=True)
    before = source.read_bytes()
    with tempfile.TemporaryDirectory() as temp:
        raster = Path(temp) / 'source.png'
        subprocess.run(['rsvg-convert', str(source), '-w', '1536', '-h', '1536', '-o', str(raster)], check=True)
        original = Image.open(raster).convert('RGBA')
        cropped = original.crop(original.getbbox())
        # Opaque white makes the original blue/orange mark readable in light/dark clients.
        email = cropped.copy(); email.thumbnail((560, 560), Image.Resampling.LANCZOS)
        email_canvas = Image.new('RGBA', (email.width + 40, email.height + 40), 'white')
        email_canvas.alpha_composite(email, (20, 20))
        email_canvas.convert('RGB').quantize(colors=128).save(frontend/'logo-imporgas.png', optimize=True)
        (backend/'logo-imporgas.png').write_bytes((frontend/'logo-imporgas.png').read_bytes())

        mark = cropped.copy(); mark.thumbnail((880, 880), Image.Resampling.LANCZOS)
        square = Image.new('RGBA', (1024, 1024))
        square.alpha_composite(mark, ((1024-mark.width)//2, (1024-mark.height)//2))
        masks = [Image.new('1', square.size, 1) for _ in COLORS]
        pixels = [mask.load() for mask in masks]
        for y in range(square.height):
            for x in range(square.width):
                red, green, blue, alpha = square.getpixel((x,y))
                if alpha < 128:
                    continue
                index = min(range(len(COLORS)), key=lambda i: sum((a-b)**2 for a,b in zip((red,green,blue), COLORS[i])))
                pixels[index][x,y] = 0
        svg = ET.Element(f'{{{NS}}}svg', {'version':'1.2','baseProfile':'tiny-ps','width':'1024','height':'1024','viewBox':'0 0 1024 1024'})
        ET.SubElement(svg, f'{{{NS}}}title').text = 'ImporGas JJ'
        ET.SubElement(svg, f'{{{NS}}}desc').text = 'Logotipo de ImporGas JJ: símbolo de llama azul y naranja sobre el nombre de la empresa.'
        ET.SubElement(svg, f'{{{NS}}}rect', {'width':'1024','height':'1024','fill':'#ffffff'})
        for i, mask in enumerate(masks):
            pbm, traced = Path(temp)/f'{i}.pbm', Path(temp)/f'{i}.svg'
            mask.save(pbm)
            subprocess.run(['potrace',str(pbm),'-s','--opttolerance','0.4','--turdsize','2','-o',str(traced)],check=True)
            tree = ET.parse(traced).getroot()
            for group in tree.findall(f'{{{NS}}}g'):
                group = copy.deepcopy(group)
                group.set('fill', '#%02x%02x%02x' % COLORS[i])
                svg.append(group)
        bimi = ET.tostring(svg, encoding='utf-8', xml_declaration=True)
        if len(bimi) > 32768:
            raise ValueError('BIMI exceeds 32 KiB; review vector simplification.')
        (frontend/'bimi-logo.svg').write_bytes(bimi)
        subprocess.run(['rsvg-convert',str(frontend/'bimi-logo.svg'),'-o',str(evidence/'bimi-render.png')],check=True)
        white = Image.new('RGBA', square.size, 'white'); white.alpha_composite(square)
        white.convert('RGB').save(evidence/'bimi-reference.png', optimize=True)
        assert source.read_bytes() == before
        report = {'source_sha256':hashlib.sha256(before).hexdigest(),'source_bytes':len(before),
                  'png_bytes':(frontend/'logo-imporgas.png').stat().st_size,
                  'png_dimensions':email_canvas.size, 'bimi_bytes':len(bimi),
                  'colors':['#001475','#f58534'],'method':'librsvg rasterization + two-color Potrace vectors; original unchanged'}
        (evidence/'asset-build.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        print(json.dumps(report))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True)
    parser.add_argument('--frontend-output', required=True)
    parser.add_argument('--backend-output', required=True)
    parser.add_argument('--evidence', required=True)
    args=parser.parse_args()
    build(args.source,args.frontend_output,args.backend_output,args.evidence)
