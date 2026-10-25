# DRISHTI Project Status

**Reviewed:** 2026-10-25  
**Scope:** contest branch and edge inference path

## Summary

DRISHTI has a working source implementation for sonar preprocessing, YOLO box detection,
confidence filtering, geotagging, reporting, a local dashboard, and a CPU-only edge API. The
edge image builds with OpenCV 5 and is now live on AWS ECS Express Mode. The project is still
**not submission ready**: the historic mAP and calibration claims have not been reproduced on
the pinned public test split, and final demo/evidence work remains.

## Verified state

| Area | Status |
|---|---|
| OpenCV 5 edge runtime | Verified in the built image: OpenCV 5.0.0, NumPy 2.5.4, ONNX Runtime 1.31.0. |
| Edge Docker image | `drishti-edge:frontend-1` built successfully; it serves the upload UI and the FastAPI/ONNX endpoints. |
| Edge upload UI | `edge/static/index.html` is served at `/` from the FastAPI container; browser upload, box overlay, detections, and model/runtime metadata are working. |
| Local edge smoke test | `/health` returned 200 with the model hash and CPU provider; `/detect` returned a shipwreck detection for the demo sample. S3 was disabled locally. |
| AWS edge service | ECS Express Mode is live in `us-east-1`; [public endpoint](https://dr-b3baa1d3c12848cdb860091b09a68618.ecs.us-east-1.on.aws). One Fargate task, 1 vCPU / 2 GB, `/health` check. |
| AWS image and results | ECR tag `drishti-9599:contest-frontend-1`; browser `/detect` stored a JSON result in `drishti95-bucket`. Bucket blocks public access, uses SSE-S3, and expires `drishti/results/` objects after 30 days. |
| AWS logs and scale | CloudWatch group `/aws/ecs/default/drishti-edge-ab52`, 14-day retention; ECS maximum task count set to 1. A monthly AWS Budget alert is not configured. |
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

The deployed frontend is the edge-specific single-image UI in `edge/static/`. The React
dashboard in `apps/dashboard` still targets Django job, WebSocket, review, and export routes and
is not part of the ECS edge service.

## Still required for submission

1. Recompute mAP and calibration on the pinned 700-tile split, or recover the exact 850-tile
   evaluation export behind the old claims. The prior 850-tile, mAP, and ECE figures are marked
   unverified and should not be presented as current results.
2. Record the host CPU and separate OpenCV preprocessing from ONNX inference latency.
3. Capture a short demo video with representative positive and empty-seabed images.
4. Set a monthly AWS Budget alert using the account owner's preferred cap and email address.
5. Recheck licensing, attribution, and the final public submission links.

## AWS state

AWS deployment is live at the endpoint listed above. The plan and operator runbook are available in
[`AWS_DEPLOYMENT_PLAN.md`](./AWS_DEPLOYMENT_PLAN.md) and [`../deploy/aws/README.md`](../deploy/aws/README.md).
The service is public and accepts unauthenticated uploads limited to 10 MB; it is capped at one task.

## Validation scope

This status reflects the edge image build, local and AWS smoke checks, dataset audit, and ONNX
evaluation performed during this workflow. The full Django/Postgres/Redis/Dashboard Compose stack
has not been smoke-tested in this review.
