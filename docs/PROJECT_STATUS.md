# DRISHTI Project Status

**Reviewed:** 2026-10-25  
**Scope:** contest branch and edge inference path

## Summary

DRISHTI has a working source implementation for sonar preprocessing, YOLO box detection,
confidence filtering, geotagging, reporting, a local dashboard, and a CPU-only edge API. The
edge image builds with OpenCV 5 and its runtime dependencies. The project is **not submission
ready yet**: it has not been deployed to AWS, and the historic mAP and calibration claims have
not been reproduced on the pinned public test split.

## Verified state

| Area | Status |
|---|---|
| OpenCV 5 edge runtime | Verified in the built image: OpenCV 5.0.0, NumPy 2.5.4, ONNX Runtime 1.31.0. |
| Edge Docker image | `drishti-edge:task4` built successfully; server module imports in the image. |
| Automated tests | 9 tests passed earlier in this workflow. The edge test run emitted a FastAPI startup-event deprecation warning. |
| Dataset splits | Pinned public dataset revision and counts verified: 3,875 train, 630 validation, 700 test (5,205 total). |
| Dataset taxonomy | Model emits five IDs; the public release has no class-0 `crab_pot` labels. Four product classes are reported. |
| Edge evaluation | Raw ONNX outputs were evaluated on all 700 test tiles at confidence 0.25 and IoU 0.50. Per-class TP/FP/FN and precision/recall are in `evaluation_manifest.yaml`. |
| PDF audit | Three technical PDFs are retained and documented; three legacy PDFs were excluded. See `PDF_AUDIT.md` and `Documents/README.md`. |

VS Code's current host interpreter reports unresolved `cv2`, `onnxruntime`, `matplotlib`, and
the dynamically added `preprocess_sonar` import. The edge image imports its runtime modules
successfully; selecting a host environment with the development dependencies will clear those
editor diagnostics.

The complete reproducibility details and numeric results are in
[`evaluation_manifest.yaml`](./evaluation_manifest.yaml). The full training/validation image
directories are incomplete locally; all label files and all test images are present for the
current audit. Dataset assets are excluded from Git.

## Still required for submission

1. Recompute mAP and calibration on the pinned 700-tile split, or recover the exact 850-tile
   evaluation export behind the old claims. The prior 850-tile, mAP, and ECE figures are marked
   unverified and should not be presented as current results.
2. Record the host CPU and separate OpenCV preprocessing from ONNX inference latency.
3. Deploy the edge service to AWS and capture `/health`, `/detect`, S3, and CloudWatch evidence.
4. Capture a short demo with representative positive and empty-seabed samples.
5. Recheck licensing, attribution, and the final public submission links.

## AWS state

AWS deployment has **not** been performed. The plan and operator runbook are available in
[`AWS_DEPLOYMENT_PLAN.md`](./AWS_DEPLOYMENT_PLAN.md) and [`../deploy/aws/README.md`](../deploy/aws/README.md).
The local image build is not an AWS deployment or a public endpoint.

## Validation scope

This status reflects the build, container import check, dataset audit, and ONNX evaluation
performed during the current workflow. The full Django/Postgres/Redis/Dashboard Compose stack
and an AWS service have not been smoke-tested in this review.
