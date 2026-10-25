from __future__ import annotations

import asyncio
from io import BytesIO

import numpy as np
import pytest
from fastapi import HTTPException
from starlette.datastructures import UploadFile

from edge import onnx_runtime_server as server
from ml.scripts.preprocess_sonar import despeckle_clahe


class _Session:
    def get_providers(self):
        return ["CPUExecutionProvider"]


class _Detector:
    size_mb = 44.8
    sess = _Session()



def test_health_reports_contest_runtime_metadata(monkeypatch):
    monkeypatch.setattr(server, "_detector", _Detector())
    monkeypatch.setattr(server, "_model_sha256", "a" * 64)
    monkeypatch.setattr(server, "_filter", object())

    response = server.health()

    assert response["opencv_version"] == server.cv2.__version__
    assert response["numpy_version"] == np.__version__
    assert response["inference_providers"] == ["CPUExecutionProvider"]
    assert response["model_sha256"] == "a" * 64
    assert response["s3_result_storage"] is False
    assert response["classes"] == ["submarine_pipeline", "shipwreck", "ghost_net", "mine_cylinder"]
    assert response["model_output_classes"][0] == "crab_pot"


def test_detect_rejects_oversized_upload(monkeypatch):
    monkeypatch.setattr(server, "_detector", _Detector())
    monkeypatch.setattr(server, "_filter", object())
    monkeypatch.setattr(server, "MAX_UPLOAD_BYTES", 4)
    upload = UploadFile(filename="sample.png", file=BytesIO(b"12345"))

    with pytest.raises(HTTPException) as error:
        asyncio.run(server.detect(upload))

    assert error.value.status_code == 413



def test_opencv_preprocessing_returns_grayscale_uint8():
    image = np.zeros((32, 32, 3), dtype=np.uint8)
    image[8:24, 8:24] = 180

    processed = despeckle_clahe(image)

    assert processed.shape == (32, 32)
    assert processed.dtype == np.uint8
