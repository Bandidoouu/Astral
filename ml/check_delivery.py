#!/usr/bin/env python
"""Verifica una entrega local contra su manifest y los resultados curados existentes.
No reentrena ni ejecuta la prueba ciega. No escribe en Backend ni Frontend.
"""
import argparse
import json
import os
from pathlib import Path

from PIL import Image

from ml.release import sha256
from ml.search import Searcher

ROOT = Path(os.environ.get('ASTRAL_ROOT', Path(__file__).resolve().parents[1]))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--release', type=Path, required=True)
    a = ap.parse_args()
    manifest = json.loads((a.release / 'manifest.json').read_text())
    assert not manifest['missing'], manifest['missing']
    for entry in manifest['files']:
        path = a.release / entry['path']
        assert path.stat().st_size == entry['bytes'], path
        assert sha256(path) == entry['sha256'], path
    searcher = Searcher(art=a.release)
    demo = json.loads((ROOT / 'frontend/src/mocks/precomputed-results.json').read_text())
    count = 0
    for site in demo['sites']:
        for key, old in site['responses'].items():
            q = old['query']
            new = searcher.search(q['body'], q['lat'], q['lon'], q['target_bodies'],
                                  old['precomputed']['k'], q['profile'], method=q['method'],
                                  scale_m=q['scale_m'], scale_mode=q.get('scale_mode', 'same_size'))
            assert old['results'] == new['results'], (site['id'], key, 'results')
            assert old['query'] == new['query'], (site['id'], key, 'query')
            count += 1
    for name in ['moon_south', 'mars']:
        assert json.loads((a.release / f'suitability/api_{name}.json').read_text()) == json.loads(
            (ROOT / f'contracts/suitability_{name}.json').read_text())
    gradcam = json.loads((a.release / 'gradcam/index.json').read_text())
    for name, digest in gradcam['source_sha256'].items():
        assert sha256(a.release / name) == digest, name
    files = {p['file'] for p in gradcam['pairs']}
    assert len(files) == gradcam['unique_figures']
    assert files == {p.name for p in (a.release / 'gradcam').glob('*.png')}
    assert gradcam['complete']
    for name in files:
        with Image.open(a.release / 'gradcam' / name) as image:
            image.verify()
    tol = gradcam['numerical_tolerance']
    for pair in gradcam['pairs']:
        assert pair['embedding_max_abs_error'] <= tol
        assert abs(pair['cosine'] - pair['recomputed_cosine_query']) <= tol
        assert abs(pair['cosine'] - pair['recomputed_cosine_result']) <= tol
    print(f'PASS: {len(manifest["files"])} SHA-256 files; {count} real responses; '
          f'2 suitability contracts; {len(files)} Grad-CAM images / {len(gradcam["pairs"])} associations')


if __name__ == '__main__':
    main()
