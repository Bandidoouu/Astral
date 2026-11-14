import json

import numpy as np

PATCH_ID = "earth-60-000123"
QUERY_ID = "moon-60-002461"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _write_heights(root, payload=None, metadata=None, patch_id=PATCH_ID):
    directory = root / "heights"
    directory.mkdir(parents=True, exist_ok=True)
    data = np.linspace(0.0, 100.0, 128 * 128, dtype=np.float32).reshape(128, 128)
    binary = data.astype("<f4").tobytes(order="C") if payload is None else payload
    (directory / f"{patch_id}.bin").write_bytes(binary)
    meta = {
        "patch_id": patch_id,
        "width": 128,
        "height": 128,
        "dtype": "float32",
        "endianness": "little",
        "min": 0.0,
        "max": 100.0,
        "m_per_px": 60,
    }
    if metadata is not None:
        meta.update(metadata)
    (directory / f"{patch_id}.json").write_text(json.dumps(meta), encoding="utf-8")


def test_heights_returns_binary_and_headers(client, artifacts_dir):
    _write_heights(artifacts_dir)
    response = client.get(f"/api/patch/{PATCH_ID}/heights")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/octet-stream"
    assert response.headers["x-min"] == "0.0"
    assert response.headers["x-max"] == "100.0"
    assert response.headers["x-m-per-px"] == "60.0"
    assert response.headers["x-width"] == "128"
    assert response.headers["x-height"] == "128"
    assert response.headers["x-dtype"] == "float32"
    assert response.headers["x-endianness"] == "little"

    array = np.frombuffer(response.content, dtype="<f4").reshape(128, 128)
    assert array.shape == (128, 128)
    assert array[0, 0] == 0.0
    assert array[-1, -1] == 100.0


def test_heights_missing_is_404(client, artifacts_dir):
    assert client.get(f"/api/patch/{PATCH_ID}/heights").status_code == 404


def test_heights_invalid_patch_id_is_404(client):
    assert client.get("/api/patch/earth-60-abc/heights").status_code == 404


def test_heights_metadata_mismatch_is_500(client, artifacts_dir):
    _write_heights(artifacts_dir, metadata={"patch_id": "earth-60-999999"})
    assert client.get(f"/api/patch/{PATCH_ID}/heights").status_code == 500


def test_heights_truncated_binary_is_500(client, artifacts_dir):
    _write_heights(artifacts_dir, payload=b"\x00" * 16)
    assert client.get(f"/api/patch/{PATCH_ID}/heights").status_code == 500


def test_heights_unsupported_dtype_is_500(client, artifacts_dir):
    _write_heights(artifacts_dir, metadata={"dtype": "float16"})
    assert client.get(f"/api/patch/{PATCH_ID}/heights").status_code == 500


def _write_gradcam(root, payload=None):
    directory = root / "gradcam"
    directory.mkdir(parents=True, exist_ok=True)
    content = PNG_SIGNATURE + b"fake-png-body" if payload is None else payload
    (directory / f"{QUERY_ID}__{PATCH_ID}.png").write_bytes(content)
    return content


def test_gradcam_returns_png(client, artifacts_dir):
    content = _write_gradcam(artifacts_dir)
    response = client.get(f"/api/gradcam/{QUERY_ID}/{PATCH_ID}")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content == content


def test_gradcam_missing_is_404(client, artifacts_dir):
    assert client.get(f"/api/gradcam/{QUERY_ID}/{PATCH_ID}").status_code == 404


def test_gradcam_invalid_query_id_is_404(client, artifacts_dir):
    _write_gradcam(artifacts_dir)
    assert client.get(f"/api/gradcam/not-a-patch/{PATCH_ID}").status_code == 404


def test_gradcam_corrupt_is_500(client, artifacts_dir):
    _write_gradcam(artifacts_dir, payload=b"not a png")
    assert client.get(f"/api/gradcam/{QUERY_ID}/{PATCH_ID}").status_code == 500
