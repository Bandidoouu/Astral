"""Offline conversion only. Requires Python, NumPy and Pillow; no frontend dependencies.
Run from any directory: python frontend/src/scenes/tools/convert_heights.py
"""
from pathlib import Path
import gzip
import hashlib
import json
import shutil
import struct
import urllib.request
import xml.etree.ElementTree as ET
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / 'tools' / '.cache'
ASSETS = ROOT / 'assets'
CACHE.mkdir(exist_ok=True)
Image.MAX_IMAGE_PIXELS = 300_000_000
WIDTH, HEIGHT = 1440, 720
URLS = {
    'earth': 'https://www.ngdc.noaa.gov/mgg/global/relief/ETOPO2022/data/60s/60s_surface_elev_gtif/ETOPO_2022_v1_60s_N90W180_surface.tif',
    'moon': 'https://svs.gsfc.nasa.gov/vis/a000000/a004700/a004720/ldem_4_uint.tif',
    'mars': 'https://pds-geosciences.wustl.edu/mgs/urn-nasa-pds-mgs_mola_topography_derived/meg004/megt90n000cb.img',
    'mars_xml': 'https://pds-geosciences.wustl.edu/mgs/urn-nasa-pds-mgs_mola_topography_derived/meg004/megt90n000cb.xml',
}

def download(key):
    url = URLS[key]
    path = CACHE / url.rsplit('/', 1)[1]
    if not path.exists():
        temporary = path.with_suffix('.part')
        print(f'Downloading {key}: {url}', flush=True)
        with urllib.request.urlopen(url, timeout=120) as response, temporary.open('wb') as output:
            shutil.copyfileobj(response, output, length=1024 * 1024)
        temporary.replace(path)
    return path

def digest(path):
    with path.open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()

def export(body, meters, source, reference, original_shape):
    assert meters.shape == (HEIGHT, WIDTH), meters.shape
    assert np.isfinite(meters).all()
    assert meters.min() > -15000 and meters.max() < 30000
    # Integer meters keep a bounded <= 0.5 m quantization error. Never normalize.
    quantized = np.rint(meters).astype('<i2')
    payload = struct.pack('<4sHH', b'ATH1', WIDTH, HEIGHT) + quantized.tobytes()
    target = ASSETS / f'{body}.height.gz'
    target.write_bytes(gzip.compress(payload, compresslevel=9, mtime=0))
    info = {
        'source_url': URLS[body], 'source_sha256': digest(source),
        'source_dimensions': original_shape, 'vertical_reference': reference,
        'width': WIDTH, 'height': HEIGHT, 'units': 'meters',
        'bounds': [-180, -90, 180, 90], 'rows': 'north to south',
        'pixel_registration': 'area; pixel centers', 'longitude': 'east-positive',
        'min_m': int(quantized.min()), 'max_m': int(quantized.max()),
        'bytes': target.stat().st_size, 'sha256': digest(target),
    }
    print(f'{body}: {info["min_m"]}..{info["max_m"]} m, {info["bytes"]} bytes', flush=True)
    return info

def main():
    result = {}
    earth = download('earth')
    with Image.open(earth) as image:
        assert image.size == (21600, 10800), image.size
        keys = tuple(image.tag_v2[34735])
        inline = {keys[i]: keys[i + 3] for i in range(4, len(keys), 4) if keys[i + 1] == 0}
        assert inline[1024] == 2 and inline[1025] == 1  # Geographic, PixelIsArea
        assert inline[2048] == 4326 and inline[4096] == 3855  # WGS84 + EGM2008 height
        assert image.tag_v2[258] == (32,) and image.tag_v2[339] == (3,)
        scale = tuple(image.tag_v2[33550])
        tie = tuple(image.tag_v2[33922])
        assert abs(scale[0] - 1 / 60) < 1e-9 and abs(scale[1] - 1 / 60) < 1e-9
        assert abs(tie[3] + 180) < 1e-6 and abs(tie[4] - 90) < 1e-6
        # 60 arcseconds -> 15 arcminutes, area average over 15x15 source cells.
        reduced = np.asarray(image.convert('F').resize((WIDTH, HEIGHT), Image.Resampling.BOX), dtype=np.float32)
    result['earth'] = export('earth', reduced, earth, 'EGM2008 geoid; ice-surface version', [21600, 10800])
    del reduced

    moon = download('moon')
    with Image.open(moon) as image:
        assert image.size == (WIDTH, HEIGHT)
        assert image.tag_v2[258] == (16,) and image.tag_v2.get(339, (1,)) == (1,)
        # NASA: unsigned counts are half-meters above radius 1727400 m.
        # Convert to meters relative to the LOLA reference sphere 1737400 m.
        meters = np.asarray(image, dtype=np.float32) * 0.5 - 10000
    result['moon'] = export('moon', meters, moon, 'LOLA sphere radius 1737400 m', [WIDTH, HEIGHT])

    mars = download('mars')
    xml_path = download('mars_xml')
    xml = ET.parse(xml_path)
    text = lambda name: [element.text.strip() for element in xml.iter() if element.tag.split('}')[-1] == name and element.text]
    assert 'SignedMSB2' in text('data_type'), text('data_type')
    assert '1440' in text('elements') and '720' in text('elements')
    assert 'East' in text('longitude_direction') or 'Positive East' in text('longitude_direction'), text('longitude_direction')
    assert text('latitude_type') == ['Planetocentric']
    assert text('axis_index_order') == ['Last Index Fastest']
    assert text('axis_name') == ['Line', 'Sample']
    assert text('west_bounding_coordinate') == ['0'] and text('east_bounding_coordinate') == ['360']
    assert text('north_bounding_coordinate') == ['90'] and text('south_bounding_coordinate') == ['-90']
    assert 'meters' in ' '.join(text('description')) and 'areoid' in ' '.join(text('description'))
    assert mars.stat().st_size == WIDTH * HEIGHT * 2
    meters = np.fromfile(mars, dtype='>i2').reshape(HEIGHT, WIDTH).astype(np.float32)
    # PDS starts at 0E; rotate columns to start at -180E, retaining north-first rows.
    meters = np.roll(meters, WIDTH // 2, axis=1)
    result['mars'] = export('mars', meters, mars, 'GMM3 areoid; presentation sphere 3396000 m', [WIDTH, HEIGHT])
    result['mars']['xml_sha256'] = digest(xml_path)
    shutil.copyfile(xml_path, ASSETS / 'mars-height.xml')
    (ASSETS / 'heights.manifest.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')

if __name__ == '__main__':
    main()
