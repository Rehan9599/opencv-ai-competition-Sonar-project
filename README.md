# DRISHTI

**AI-powered underwater marine-debris & anomaly detection from side-scan sonar imagery.**
OpenCV AI Competition 2026, powered by AWS · OpenCV 5 · Physical AI

DRISHTI ingests a raw side-scan sonar (SSS) transect, detects man-made seabed hazards
(shipwrecks, pipelines/cables, cylinders, entangled "ghost" nets), scores each detection on a
**calibrated 0–100 %** scale, geotags it to latitude/longitude with an honest uncertainty
radius, and emits a JSON / CSV / GeoJSON report plus a live review dashboard — the detector runs
**torch-free on a CPU**, edge-deployable, no cloud required.

> Three retained technical PDFs document preprocessing, model selection, and system limitations;
> see [`docs/Documents/README.md`](docs/Documents/README.md) and [`docs/PDF_AUDIT.md`](docs/PDF_AUDIT.md).
> Contest architecture and submission notes: [`docs/OPENCV_AI_COMPETITION_2026.md`](docs/OPENCV_AI_COMPETITION_2026.md).

## OpenCV AI Competition 2026

This contest branch is prepared for the [OpenCV AI Competition 2026, powered by AWS](https://opencv.org/competition/).
OpenCV performs substantive sonar image analysis through decoding, Lee speckle filtering,
CLAHE enhancement, resizing, and annotated output preparation. ONNX Runtime remains the
neural inference engine so the CPU path stays reproducible and lightweight.

The contest deployment target is a focused edge API rather than the full local Django stack:

- OpenCV 5 preprocessing and image analysis
- ONNX Runtime CPU inference
- Containerized FastAPI service in `edge/`
- Optional S3 result storage through the task's IAM role
- CloudWatch-compatible container logs
- AWS ECS/Fargate or App Runner deployment

See [`docs/OPENCV_AI_COMPETITION_2026.md`](docs/OPENCV_AI_COMPETITION_2026.md) for the
submission requirements, architecture, evaluation claims, and responsible-use limitations.
The current project status is [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md), and the
reproducibility record is [`docs/evaluation_manifest.yaml`](docs/evaluation_manifest.yaml).

**Try the detector in 2 minutes, no setup:**
[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Rehan9599/opencv-ai-competition-Sonar-project/blob/main/notebooks/01_quickstart_inference.ipynb)
— the ONNX model and sample tiles are committed, so one `git clone` runs the detector on CPU.

---

## 1. Repository layout

```
apps/
  api/            Django REST + Channels (WebSocket) + Celery worker  →  the backend service
    detections/   models · views · serializers · tasks (the ML job)  · tiling · consumers · routing
    drishti_api/  settings · asgi · celery
  dashboard/      React 18 + Vite + React-Leaflet  →  the operator dashboard (Module 4)
    src/components/  UploadPanel · MapView · ReviewQueue · DetectionImage
    src/pages/       UploadResultsPage (the one working page) · LiveFeed · GlobalMap · Export
    src/state/       store.js  (session-scoped job accumulation)
ml/
  scripts/        dataset assembly · preprocess · train · calibrate · evaluate · export_onnx · run_aurora_survey
  inference/      detector · confidence_filter · shadow_verification · preprocess · pipeline (chains M0→M3)
  geotagging/     XTF header parser · nav CSV · coordinate projection · run_geotag
  reporting/      schema · json_export · csv_export
  models/         checkpoints/ (best_detector.pt) · exported/ (ONNX + calibrator.pkl)
edge/             torch-free inference: edge_infer.py · onnx_runtime_server.py · benchmark.py · Dockerfile.edge
demo/             frontend_test/ (curated upload bundle) · preprocessing_demo.py · tiles/
docs/             Documents/ (3 retained PDFs) · API_ENDPOINTS.md · LOCAL_SETUP.txt · TILING_DEDUP_FIX.md
                  OpenCV competition/AWS plans · evaluation manifest · PDF audit · hf/ cards
compose.yaml      full local stack: postgres + redis + web + worker
scripts/run_local.sh   native fallback (Postgres+Redis in Docker, Django+Celery on the host)
notebooks/        Colab quickstart
```

Training data (~34 GB) and weight backups are **not in git** — see §5.

---

## 2. Run it locally

The stack is 4 services: **Postgres · Redis · Django (ASGI) · Celery worker**, plus the Vite dev server.

### 2.1 Docker (recommended)

```bash
cp .env.example .env
docker compose up -d --build                       # postgres + redis + web + worker
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser

# frontend (separate terminal)
npm install -g pnpm
pnpm install
pnpm --filter @drishti/dashboard dev               # → http://localhost:5173
```

API on `http://localhost:8000`, dashboard on `http://localhost:5173` (Vite proxies `/api` and
`/ws` to `:8000`). Postgres is published on host port **5433** (container-internal 5432) so it
won't clash with a native Postgres — `compose.yaml` overrides `POSTGRES_PORT` back to 5432
inside the network.

> **`docker compose build worker` after any change to `apps/api/detections/tasks.py`** — the
> worker image is `FROM drishti-api:latest`, so a `web`-only rebuild silently ships stale task code.

### 2.2 Native fallback (no Docker for the app)

`scripts/run_local.sh` runs Postgres + Redis in Docker but Django (`daphne`) and Celery
(`-P solo`, required on Windows) natively from `.venv`:

```bash
python -m venv .venv && source .venv/Scripts/activate     # or bin/activate
pip install -r apps/api/requirements.txt
bash scripts/run_local.sh
pnpm --filter @drishti/dashboard dev
```

Full detail, troubleshooting, and the known-issues list: **`docs/LOCAL_SETUP.txt`**.

### 2.3 Smoke test

```bash
curl -F "file=@demo/frontend_test/02_shipwreck.jpg" \
     -F "nav=@demo/frontend_test/navigation.csv" \
     http://localhost:8000/api/upload/                    # → {"job_id": "..."}
```

`demo/frontend_test/` has five curated tiles (pipeline, shipwreck, mine, ghost-net, empty
seabed) + a real AURORA nav CSV + one full transect TIF. See its `README.md` for the exact
drag-and-drop demo script.

---

## 3. The dashboard (Module 4 — working)

The `/upload` page is the operational surface. All of this is wired to the live API:

- **Multi-file upload** — drop several tiles at once; each becomes its own job, results merge.
- **Session accumulation** — every upload this browser session stays on one map + review
  queue (backed by `sessionStorage`; a `settled` flag gates polling so a job's results are
  fetched exactly once, and never revert to the raw pre-merge stream).
- **Live streaming** — detections appear tile-by-tile over WebSocket while the job runs, then
  reconcile to the final de-duplicated set on completion.
- **Map** — geolocated contacts with a per-class colour, an uncertainty circle (not a false
  point), and a hover popup. "Show detected image" opens the source tile crop with the box
  drawn (`GET /api/detections/<id>/image/`).
- **Review queue** — pinned header, scrolls independently, per-row Confirm / Reject. Every
  decision writes an `AuditLogEntry` and becomes a fine-tuning label.
- **Export** — JSON / CSV / GeoJSON per job, straight into existing GIS tools.
- **Single-viewport layout** — map + review queue + export fit one screen, no page scroll.

---

## 4. The model & pipeline

### 4.1 Model

- **YOLOv8s**, fine-tuned from COCO (Ultralytics 8.4.x), **anchor-free**, 11.8 M params.
- **Box detection**, not segmentation — every real SSS dataset we could obtain is box-labelled.
- **4 classes shipped** (`submarine_pipeline`, `shipwreck`, `mine_cylinder`, `ghost_net`);
  `crab_pot` was trained then filtered from the product (separability, not data volume — see
  the model doc), and is excluded from the public dataset for licensing.
- **SSS-specific training:** grayscale, **vertical-flip OFF** (preserves highlight→shadow
  polarity), 640 px, 120 epochs, AdamW, best checkpoint @ epoch 91.
- **Preprocessing (M0):** Lee MMSE speckle filter (7×7) + CLAHE (clip 3.0, 8×8), identical at
  train and serve time — `ml/scripts/preprocess_sonar.py :: despeckle_clahe`.
  `demo/preprocessing_demo.py` renders a raw → Lee → Lee+CLAHE before/after panel.

### 4.2 Reproduced ONNX results — published test split

The public dataset revision audited for this submission has **700 test tiles**. The prior
850-tile and mAP claims do not have a matching evaluation export, so they are not treated as
verified results. The reproducible ONNX check below uses confidence `0.25`, one-to-one
same-class matching at IoU `0.50`, and the 700 published test tiles:

This is the raw ONNX detector at one shared confidence threshold. The server's per-class
confidence gates and calibration are not applied in this diagnostic run.

| Shipped class | TP | FP | FN | Precision | Recall |
|---|---:|---:|---:|---:|---:|
| `submarine_pipeline` | 168 | 6 | 6 | 0.9655 | 0.9655 |
| `shipwreck` | 180 | 100 | 345 | 0.6429 | 0.3429 |
| `ghost_net` | 120 | 0 | 0 | 1.0000 | 1.0000 |
| `mine_cylinder` | 38 | 26 | 44 | 0.5938 | 0.4634 |

These are fixed-threshold precision/recall figures, **not mAP**. `ghost_net` is synthetic-only,
so its result is capability evidence, not field performance. See
[`docs/evaluation_manifest.yaml`](docs/evaluation_manifest.yaml) for the dataset revision,
model hash, method, and remaining evaluation gates.

Context: vanilla YOLOv8 tops out at ~0.716–0.755 mAP on clean AI4Shipwrecks in the 2026
literature (DFSE-YOLO); human annotators agree only 50–60 % on wreck boundaries (SW-Net).

### 4.3 Pipeline (per job)

```
raw SSS transect + nav log
        │
        ▼
  tile 640×640, 50 % overlap (stride 320)        ── for every tile ──┐
        │                                                            │
        ▼                                                            │
  M0  preprocess   Lee 7×7 + CLAHE                                    │
        ▼                                                            │
  M1  detect       YOLOv8s → box + class + raw score                 │
        ▼                                                            │
  M2  confidence   per-class gate → per-class Platt calibration →    │
                   acoustic-shadow geometry check  (L = h·G/(H−h))   │
        ▼                                                            │
  M3  geotag       pixel → slant range R → ground range G=√(R²−H²) → │
                   geodesic step ⟂ heading → (lat, lon) + size (m)   │
        └────────────────────────────────────────────────────────────┘
        ▼
  merge duplicates across overlapping tiles   (centre-distance ≤ 50 px, per class)
        ▼
  route by calibrated score   ≥ 80 auto-confirm · 30–80 review queue · < 30 drop
        ▼
  JSON / CSV / GeoJSON  +  live dashboard
```

- Single tile: `python -m ml.inference.pipeline --image tile.png --xtf <f>.xtf --nav navigation.csv --out report`
- Full transect: `python ml/scripts/run_aurora_survey.py --preprocess`
- Geotag validated on the AURORA survey to **< 1 m** against recorded navigation; the *target*
  projection is a different quantity — two nav paths placed the same contact ~122 m apart, so
  every detection carries a **search radius and a `ping_id`, never a bare pin**.
- No nav source? The pipeline still runs — detections get `null` coordinates and stay off the
  map, class/score/box intact.

### 4.4 Edge / ONNX

| Model | Size | CPU latency | Role |
|---|---|---|---|
| **FP32 ONNX** | 44.8 MB | ~90 ms/tile (98–106 ms on a laptop CPU) | **shipped** — `onnxruntime` + `numpy` + `opencv`, no PyTorch |
| FP16 ONNX | 22.4 MB | — | Jetson Orin GPU target (FP16/TensorRT) |
| INT8 ONNX | 11.5 MB | 164 ms (slower) + accuracy collapse | excluded |

```bash
python ml/scripts/export_onnx.py --model ml/models/checkpoints/best_detector.pt --benchmark
python edge/edge_infer.py --image tile.png --no-preprocess
uvicorn edge.onnx_runtime_server:app --port 8100
```

The edge health response reports the actual OpenCV, NumPy, and ONNX Runtime versions, model
SHA-256, inference provider, model output classes, and four-class product taxonomy. Use it as
the runtime evidence for the contest report:

```bash
curl http://localhost:8100/health
```

The Celery worker imports `ml.inference.pipeline.run_pipeline()` **in-process** — the model is a
library, not a microservice. Redis carries messages only; detections go worker → Postgres via
`bulk_create`.

---

## 5. Data & weights

**Committed (≈ 65 MB), so `git clone` runs the detector with no fetch step:**

| File | Size | Used by |
|---|---|---|
| `ml/models/checkpoints/best_detector.pt` | 21.5 MB | `pipeline.py` default (needs torch) |
| `ml/models/exported/best_detector.onnx` | 44.8 MB | torch-free `onnxruntime` path (backend + edge) |
| `ml/models/exported/calibrator.pkl` | 2 KB | M2 per-class calibration |

**Not in git:**

| Asset | Source |
|---|---|
| `.pt` backups, FP16/INT8 ONNX, per-epoch checkpoints (~3.4 GB) | [`rehan9599/drishti-detector`](https://huggingface.co/rehan9599/drishti-detector) — `hf download rehan9599/drishti-detector` |
| Training splits — 5,205 tiles, preprocessed, **CC-BY-SA-4.0** | [`rehan9599/drishti-sss`](https://huggingface.co/datasets/rehan9599/drishti-sss) — `hf download rehan9599/drishti-sss --repo-type dataset --local-dir ml/data/splits` |
| Raw source datasets (~32 GB) | reconstructible — public sources listed in the literature doc + `ml/scripts/tile_*.py` + `build_dataset.py` |

**Licences:** AI4Shipwrecks · SubPipe · Roboflow SSS — CC-BY-4.0 · Kaggle sonar-mine — CC-BY-SA-4.0.
KLSG / SeabedObjects **excluded** (academic-use only, no redistribution). Our assembled release: CC-BY-SA-4.0.

---

## 6. API

Full contract: **`docs/API_ENDPOINTS.md`**.

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/upload/` | multipart `file` (+ optional `xtf`, `nav`) → `{job_id}`, `202` |
| `GET` | `/api/jobs/` · `/api/jobs/<id>/` | job list / status + progress |
| `GET` | `/api/detections/<job_id>/` | the 13-field detection records (`job_id` included) |
| `PATCH` | `/api/detections/<id>/review/` | `{review_status: analyst_confirmed \| analyst_rejected}` → audit entry |
| `GET` | `/api/detections/<id>/image/` | source tile crop with the bounding box drawn |
| `GET` | `/api/export/<job_id>/?format=json\|csv\|geojson` | report download |
| `WS` | `/ws/jobs/<job_id>/` | `detection.partial` (per tile) · `detection.complete` · `detection.failed` |

---

## 7. Docs

| File | What |
|---|---|
| `docs/Documents/` | three retained technical PDFs; purpose and status are listed in `docs/Documents/README.md` |
| `docs/OPENCV_AI_COMPETITION_2026.md` | contest architecture, evidence, and submission requirements |
| `docs/PROJECT_STATUS.md` | current verified state and remaining submission gates |
| `docs/AWS_DEPLOYMENT_PLAN.md` | AWS deployment plan and evidence checklist |
| `docs/evaluation_manifest.yaml` | pinned dataset, model, runtime, and verified evaluation details |
| `docs/PDF_AUDIT.md` | PDF retention and regeneration decisions |
| `docs/API_ENDPOINTS.md` | REST + WebSocket contract |
| `docs/LOCAL_SETUP.txt` | end-to-end local bring-up + troubleshooting + known issues |
| `docs/TILING_DEDUP_FIX.md` | cross-tile duplicate-detection bug: root cause + fix + verification (backend-team report) |
| `docs/hf/` | Hugging Face model + dataset cards |

---

## 8. What changed in this revision

Backend / ML:
- **Cross-tile duplicate merge** — `_merge_overlapping_detections()` runs once per job after all
  tiles are scored, collapsing near-identical detections of the same class (bbox-centre ≤ 50 px)
  and keeping the highest-confidence one. Logged to the completion audit entry. (`docs/TILING_DEDUP_FIX.md`)
- **True 50 % tile overlap** — `write_tiles()` / `tile_offsets()` stride `512 → 320`.
- **`DetectionSerializer`** — explicit 13-field list, `job_id` now included (was dropped by `exclude`).
- **`GET /api/detections/<id>/image/`** — regenerates the source tile crop with the box drawn
  (tiles are transient; the upload + full-image bbox are kept).
- **Ungeotagged records** — `run_pipeline` emits detections with `null` lat/lon when no
  nav/XTF is supplied instead of erroring; `schema.py` / `json_export.py` handle null geometry.
- **Docker** — `.dockerignore` (image 30 GB → 1.2 GB, build 40 min → 2 min), pip cache mount,
  HTTPS apt; `compose.yaml` Postgres host-port 5433 + in-network port override.

Frontend:
- **Session-accumulating results** with a `settled` polling gate (`store.js`, `UploadResultsPage.jsx`).
- **Multi-file upload** (`UploadPanel.jsx`).
- **"Show detected image" modal** with a graceful "not available yet" fallback (`DetectionImage/`).
- **Map hover popup**; **review queue** pinned-header scroll fix.
- **Single-viewport layout** — map + queue + export on one screen.

Infra / demo / docs:
- `scripts/run_local.sh` (native stack), `docs/LOCAL_SETUP.txt`, `docs/TILING_DEDUP_FIX.md`.
- `demo/frontend_test/` (curated upload bundle + AURORA nav), `demo/preprocessing_demo.py`
  (Lee + CLAHE before/after).
- `docs/Documents/*.pdf` — the three retained technical references; see `docs/Documents/README.md`.

---

## 9. Status

| Part | State |
|---|---|
| OpenCV 5 edge image | **verified** — OpenCV 5.0.0, NumPy 2.5.4, ONNX Runtime 1.31.0 |
| Edge Docker build | **passed locally** — `drishti-edge:task4`; no AWS deployment yet |
| Edge tests | **9 passed** earlier in this workflow; FastAPI startup-event deprecation warning remains |
| Dataset and taxonomy | **reconciled** against the pinned 5,205-tile public dataset; four shipped classes |
| Evaluation | fixed-threshold ONNX P/R reproduced on 700 test tiles; historic mAP/ECE claims remain unverified |
| Local Django/dashboard stack | source is present; full Compose stack was not smoke-tested in this review |
| AWS deployment and demo evidence | **pending** |

See [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md) for validation details and the remaining submission gates.
