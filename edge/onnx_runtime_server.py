"""
Lightweight FastAPI microservice for on-vehicle / edge inference.

Same JSON contract as the Django API's detection response, so the frontend needs
zero changes whether inference ran server-side or here. Torch-free: the whole
request path is onnxruntime + numpy + opencv (see edge/edge_infer.py).

  Tier 0 (laptop / AUV compute): CPUExecutionProvider   -> this file, as is
  Tier 1 (Jetson):               onnxruntime-gpu + TensorRTExecutionProvider

Run:
  pip install -r edge/requirements.txt
  uvicorn edge.onnx_runtime_server:app --host 0.0.0.0 --port 8100
"""

from __future__ import annotations

import hashlib
import logging
import os
import sys
import time
from pathlib import Path

import cv2
import numpy as np
import onnxruntime as ort

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "ml" / "scripts"))

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse

from edge.edge_infer import (
    EdgeDetector,
    DEFAULT_ONNX,
    DEFAULT_CAL,
    CLASS_NAMES,
    SHIPPED_CLASS_NAMES,
)
from preprocess_sonar import despeckle_clahe
from ml.inference.confidence_filter import ConfidenceFilter
from edge.storage import is_enabled, store_result

ONNX_PATH = Path(os.environ.get("DRISHTI_ONNX", DEFAULT_ONNX))
CAL_PATH = Path(os.environ.get("DRISHTI_CALIBRATOR", DEFAULT_CAL))
PREPROCESS = os.environ.get("DRISHTI_PREPROCESS", "1") != "0"
MAX_UPLOAD_BYTES = int(os.environ.get("DRISHTI_MAX_UPLOAD_BYTES", str(10 * 1024 * 1024)))
if MAX_UPLOAD_BYTES <= 0:
    raise ValueError("DRISHTI_MAX_UPLOAD_BYTES must be a positive integer")

RUNTIME_NAME = "onnxruntime-cpu"

app = FastAPI(title="DRISHTI edge inference", version="1.0")
logger = logging.getLogger("drishti.edge")

_detector: EdgeDetector | None = None
_filter: ConfidenceFilter | None = None
_model_sha256: str | None = None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as model_file:
        for chunk in iter(lambda: model_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@app.on_event("startup")
def _load():
    global _detector, _filter, _model_sha256
    if not ONNX_PATH.exists():
        raise RuntimeError(f"ONNX model not found: {ONNX_PATH} — run ml/scripts/export_onnx.py")
    _detector = EdgeDetector(ONNX_PATH)
    _model_sha256 = _sha256(ONNX_PATH)
    _filter = ConfidenceFilter(
        calibrator_path=str(CAL_PATH) if CAL_PATH.exists() else None,
        use_shadow_check=False,          # tiles: no per-ping geometry
    )


@app.get("/health")
def health():
    return {
        "status": "ok",
        "runtime": RUNTIME_NAME,
        "opencv_version": cv2.__version__,
        "numpy_version": np.__version__,
        "onnxruntime_version": ort.__version__,
        "model": ONNX_PATH.name,
        "model_sha256": _model_sha256,
        "model_size_mb": round(_detector.size_mb, 2) if _detector else None,
        "inference_providers": _detector.sess.get_providers() if _detector else [],
        "preprocess": PREPROCESS,
        "max_upload_bytes": MAX_UPLOAD_BYTES,
        "s3_result_storage": is_enabled(),
        "model_output_classes": CLASS_NAMES,
        "classes": SHIPPED_CLASS_NAMES,
    }


@app.post("/detect")
async def detect(file: UploadFile = File(...)):
    """One sonar tile in -> filtered, scored detections out (API-contract shape)."""
    if _detector is None or _filter is None:
        raise HTTPException(503, "model not loaded")
    raw_bytes = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(raw_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, f"file exceeds {MAX_UPLOAD_BYTES} byte limit")
    if not raw_bytes:
        raise HTTPException(400, "uploaded file is empty")
    raw = np.frombuffer(raw_bytes, np.uint8)
    bgr = cv2.imdecode(raw, cv2.IMREAD_COLOR)
    if bgr is None:
        raise HTTPException(400, "could not decode image")
    if PREPROCESS:
        bgr = cv2.cvtColor(despeckle_clahe(bgr), cv2.COLOR_GRAY2BGR)

    t0 = time.perf_counter()
    dets_raw = _detector.detect(bgr, conf=0.10)
    scored = _filter.filter(dets_raw)
    infer_ms = round((time.perf_counter() - t0) * 1000, 1)

    response = {
        "source_file": file.filename or "upload",
        "runtime": RUNTIME_NAME,
        "opencv_version": cv2.__version__,
        "inference_ms": infer_ms,
        "detections": [
            {
                "class_label": d["class_label"],
                "confidence_score": d["confidence_score"],
                "bounding_geometry": {
                    "bbox": d["bbox"],
                    "mask_polygon": [],
                    "width_m": None,
                    "height_m": None,
                },
                "review_status": "auto_confirmed" if d["confidence_score"] >= 80 else "pending_review",
            }
            for d in scored
        ],
    }
    try:
        result_uri = store_result(response)
    except Exception as exc:
        logger.exception("S3 result storage failed")
        if is_enabled():
            raise HTTPException(502, "result storage failed") from exc
        result_uri = None
    if result_uri:
        response["result_uri"] = result_uri
    return JSONResponse(response)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("edge.onnx_runtime_server:app", host="0.0.0.0", port=8100, reload=False)
