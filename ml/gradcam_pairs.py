#!/usr/bin/env python
"""Grad-CAM del coseno de terreno con las cuatro rotaciones de ml.embed.

Genera una figura por par de parches único y conserva todas las asociaciones con
sitios curados en index.json. No explica el ranking RRF ni dimensiones ambientales.
No reentrena ni modifica embeddings. Primero probar --limit 1 --output <muestra>.
"""
import argparse
import json
import os
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F

from ml.embed import load_encoder
from ml.model.channels import make_channels
from ml.release import sha256

ROOT = Path(os.environ.get('ASTRAL_ROOT', Path(__file__).resolve().parents[1]))
ART = ROOT / 'data/artifacts'


def curated_pairs(doc, top=3):
    """Los nombres de sitio pertenecen al índice, no a la figura compartida."""
    pairs = []
    for site in doc['sites']:
        response = site['responses']['1000']
        for target in sorted({r['body'] for r in response['results']}):
            query = response['query']['patches'][target]
            for rank, result in enumerate([r for r in response['results'] if r['body'] == target][:top], 1):
                qid, rid = query['patch_id'], result['patch_id']
                pairs.append(dict(site_id=site['id'], site=site['name'], query_patch_id=qid,
                                  query_distance_km=query['distance_km'], target=target, rank=rank,
                                  result_patch_id=rid, region=result['region'],
                                  terrain_score=result['scores']['terrain'], file=f'{qid}__{rid}.png'))
    return pairs


def rotation_channels(z, pixel_m):
    return torch.cat([make_channels(torch.rot90(z, k, (2, 3)), pixel_m) for k in range(4)])


def explain(enc, channels, concept, expected, tolerance):
    """Grad-CAM de dot(normalize(sum(enc(rotaciones))), embedding fijo del otro).

Un forward con batch de cuatro vistas captura layer4. Promediamos los gradientes
espaciales por canal, desrotamos los CAM crudos, promediamos, aplicamos ReLU y
normalizamos una sola vez. Así no igualamos artificialmente las cuatro vistas.
    """
    captured = []
    handle = enc.backbone.layer4.register_forward_hook(lambda module, args, out: captured.append(out))
    try:
        with torch.autocast('cuda', dtype=torch.bfloat16, enabled=channels.is_cuda):
            views = enc(channels.contiguous(memory_format=torch.channels_last))
        embedding = F.normalize(views.float().sum(0), dim=0)
        cosine = (embedding * concept).sum()
        error = float(torch.max(torch.abs(embedding.detach() - expected)))
        if error > tolerance:
            raise ValueError(f'Recomputed embedding differs from index by {error:.6f} > {tolerance}')
        activation = captured[0]
        gradient, = torch.autograd.grad(cosine, activation)
        raw = (gradient.float().mean((2, 3), keepdim=True) * activation.float()).sum(1)
        aligned = torch.stack([torch.rot90(raw[k], -k, (0, 1)) for k in range(4)]).mean(0)
        heat = F.interpolate(aligned[None, None], size=channels.shape[-2:], mode='bilinear',
                             align_corners=False)[0, 0].clamp_min(0)
        peak = float(heat.max().detach())
        heat = heat / peak if peak > 0 else heat
        if not torch.isfinite(heat).all():
            raise ValueError('Nonfinite Grad-CAM')
        return heat.detach().cpu().numpy(), float(cosine.detach()), error, peak
    finally:
        handle.remove()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', type=Path, default=ART / 'gradcam')
    ap.add_argument('--demo', type=Path, default=ROOT / 'frontend/src/mocks/precomputed-results.json')
    ap.add_argument('--limit', type=int, help='Número de pares únicos para prueba pequeña')
    ap.add_argument('--tolerance', type=float, default=0.005, help='Tolerancia numérica BF16 por componente')
    a = ap.parse_args()
    if a.limit is not None and a.limit < 1:
        ap.error('--limit must be positive')
    # Evita sobrescribir una entrega anterior o mezclar una prueba con un paquete.
    a.output.mkdir(parents=True, exist_ok=False)
    doc = json.loads(a.demo.read_text())
    pairs = curated_pairs(doc)
    files = list(dict.fromkeys(p['file'] for p in pairs))
    if a.limit:
        files = files[:a.limit]
    pairs = [p for p in pairs if p['file'] in files]
    meta = pd.read_parquet(ART / 'meta_1000.parquet')
    positions = {pid: i for i, pid in enumerate(meta.patch_id)}
    vectors = np.load(ART / 'emb_1000.npy')
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    enc = load_encoder(ART / 'encoder_v2_1000.pt', device=device).float().eval()
    arrays = {}

    def patch(pid):
        idx = positions[pid]
        row = meta.iloc[idx]
        if row.src not in arrays:
            arrays[row.src] = np.load(ROOT / f'data/patches/patches_{row.src}.npy', mmap_mode='r')
        z = torch.tensor(np.array(arrays[row.src][int(row.src_idx)], np.float32), device=device)[None, None]
        px = torch.tensor([float(row.scale_m)], device=device)
        return row, rotation_channels(z, px), torch.tensor(vectors[idx], device=device)

    for number, name in enumerate(files, 1):
        entries = [p for p in pairs if p['file'] == name]
        entry = entries[0]
        qr, qx, qe = patch(entry['query_patch_id'])
        rr, rx, re = patch(entry['result_patch_id'])
        index_cosine = float((qe * re).sum())
        for item in entries:
            if abs(np.clip(index_cosine, 0, 1) - item['terrain_score']) > 0.001:
                raise ValueError(f'Demo/index mismatch: {name}')
        cq, cosq, eq, pq = explain(enc, qx, re, qe, a.tolerance)
        cr, cosr, er, pr = explain(enc, rx, qe, re, a.tolerance)
        if max(abs(cosq-index_cosine), abs(cosr-index_cosine)) > a.tolerance:
            raise ValueError(f'Cosine mismatch: {name}')
        fig, axes = plt.subplots(1, 2, figsize=(10, 5.6))
        for ax, x, heat, row, label in [(axes[0], qx, cq, qr, 'Query patch'),
                                       (axes[1], rx, cr, rr, 'Result patch')]:
            ax.imshow(x[0, 4].cpu().numpy(), cmap='gray', vmin=0, vmax=1)
            ax.imshow(heat, cmap='inferno', alpha=0.55 * heat, vmin=0, vmax=1)
            ax.set_title(f'{label}: {row.patch_id}\n{row.lat:.2f}°, {row.lon:.2f}° · 128 km window', fontsize=9)
            ax.set_xticks([]); ax.set_yticks([])
        fig.suptitle(f'Terrain similarity attribution · v2 (1 km, same_size)\nIndex cosine {index_cosine:.3f} · four-rotation Grad-CAM', fontsize=12)
        fig.text(.5, .04, 'Brighter overlay = stronger positive Grad-CAM attribution (normalized per panel).\n'
                 'Approximate, coarse localization; not a causal explanation or an RRF / environmental score explanation.\n'
                 'LOLA / MOLA / SRTMGL30 hillshade. Curated sites may share a query patch; see index.json.',
                 ha='center', fontsize=8)
        fig.subplots_adjust(top=.79, bottom=.20)
        fig.savefig(a.output / name, dpi=120, facecolor='#fcfcfb')
        plt.close(fig)
        for item in entries:
            item.update(cosine=round(index_cosine, 6), recomputed_cosine_query=cosq,
                        recomputed_cosine_result=cosr, embedding_max_abs_error=max(eq, er),
                        query_cam_peak=pq, result_cam_peak=pr)
        print(f'{number}/{len(files)} {name} cosine error={max(abs(cosq-index_cosine), abs(cosr-index_cosine)):.6f}', flush=True)
    provenance = {f: sha256(ART / f) for f in ['encoder_v2_1000.pt', 'meta_1000.parquet', 'emb_1000.npy']}
    result = dict(model='v2', encoder='encoder_v2_1000.pt', layer='backbone.layer4', scale_m=1000,
                  scale_mode='same_size', rotations=4, unique_figures=len(files), complete=a.limit is None,
                  objective='cosine of normalized sum of four rotated embeddings against fixed indexed counterpart',
                  aggregation='inverse-rotate raw CAMs, mean, resize, ReLU, normalize per panel',
                  numerical_tolerance=a.tolerance, source_sha256=provenance, demo_sha256=sha256(a.demo), pairs=pairs)
    (a.output / 'index.json').write_text(json.dumps(result, indent=2, allow_nan=False))
    (a.output / 'README.md').write_text(
        '# ASTRAL Grad-CAM\n\n'
        f'{len(pairs)} curated-site associations; {len(files)} unique patch-pair figures.\n\n'
        'Scope: v2, 1000 m/px, same_size, top three RRF results per destination. '
        'Each figure explains the neural terrain cosine only, not the RRF rank or environmental scores.\n\n'
        'Multiple sites may use the same nearest indexed patch. Figures identify actual patches; '
        'index.json retains site names, ranks and query distances without overwriting titles.\n\n'
        'Gradients pass through the normalized sum of four 90-degree views, matching the embedding recipe. '
        'Each side uses the fixed indexed embedding of its counterpart. BF16/batch differences are '
        'checked against indexed embeddings and cosine; exact errors and source SHA-256 are in index.json.\n\n'
        'Grad-CAM is a coarse, approximate attribution, not proof of causation or geological equivalence. '
        'Brightness is normalized independently per panel; an empty positive CAM remains empty. '
        'It does not explain gravity_scaled or 60 m searches.\n')
    print(f'Finished: {len(pairs)} associations, {len(files)} unique figures -> {a.output}')


if __name__ == '__main__':
    main()
