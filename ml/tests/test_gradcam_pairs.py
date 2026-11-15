"""Pruebas de atribución TTA y asociaciones de sitios; ejecutar con unittest."""
import unittest

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F

from ml.gradcam_pairs import curated_pairs, explain


class ToyEncoder(nn.Module):
    def __init__(self):
        super().__init__()
        self.backbone = nn.Module()
        self.backbone.layer4 = nn.Identity()

    def forward(self, x):
        return F.normalize(self.backbone.layer4(x).mean((2, 3)), dim=1)


class GradCAMTests(unittest.TestCase):
    def test_shared_patch_preserves_both_sites_and_one_filename(self):
        response = {'query': {'patches': {'earth': {'patch_id': 'moon-1000-1', 'distance_km': 42}}},
                    'results': [{'body': 'earth', 'patch_id': 'earth-1000-2', 'region': 'Test',
                                 'scores': {'terrain': .8}}]}
        doc = {'sites': [dict(id=n, name=n, responses={'1000': response}) for n in ['A', 'B']]}
        pairs = curated_pairs(doc)
        self.assertEqual([p['site'] for p in pairs], ['A', 'B'])
        self.assertEqual(len({p['file'] for p in pairs}), 1)
        self.assertEqual(pairs[0]['query_distance_km'], 42)

    def test_cosine_and_cam_follow_normalized_sum_of_views(self):
        torch.manual_seed(5)
        channels = torch.rand(4, 3, 8, 8, requires_grad=True)
        model = ToyEncoder()
        concept = F.normalize(torch.tensor([.9, -.3, .1]), dim=0)
        # Referencia independiente: gradiente analítico de normalización, por vista.
        means = channels.detach().mean((2, 3))
        norms = means.norm(dim=1, keepdim=True)
        views = means / norms
        summed = views.sum(0)
        expected = summed / summed.norm()
        ds = (concept - expected * (expected @ concept)) / summed.norm()
        dm = (ds - views * (views * ds).sum(1, keepdim=True)) / norms
        raw = (channels.detach() * (dm / 64)[:, :, None, None]).sum(1)
        ref = torch.stack([torch.rot90(raw[k], -k, (0, 1)) for k in range(4)]).mean(0).clamp_min(0)
        ref = ref / ref.max()
        heat, cosine, error, peak = explain(model, channels, concept, expected, 1e-6)
        np.testing.assert_allclose(heat, ref.numpy(), atol=2e-6)
        self.assertAlmostEqual(cosine, float(expected @ concept), places=6)
        self.assertLess(error, 1e-6)
        self.assertGreater(peak, 0)

    def test_stale_embedding_is_rejected_and_hook_removed(self):
        model = ToyEncoder()
        channels = torch.ones(4, 3, 8, 8, requires_grad=True)
        with self.assertRaisesRegex(ValueError, 'differs from index'):
            explain(model, channels, torch.ones(3), torch.zeros(3), .005)
        self.assertFalse(model.backbone.layer4._forward_hooks)


if __name__ == '__main__':
    unittest.main()
