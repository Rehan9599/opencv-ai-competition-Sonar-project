# OpenCV AI Competition 2026

DRISHTI is being prepared for the **OpenCV AI Competition 2026, powered by AWS**.

## Competition requirements

- OpenCV 5 must perform substantive image or video analysis.
- The project must use a meaningful AWS component.
- The final project is due October 27, 2026 at 12:15 PM IST according to the current Devpost listing.
- The submission must document reproducibility, evaluation, limitations, and responsible use.

## DRISHTI contest implementation

- OpenCV: sonar decoding, Lee speckle filtering, CLAHE enhancement, resizing, and annotation.
- Inference: ONNX Runtime on CPU.
- AWS target: containerized FastAPI inference API with optional S3 result storage.
- Deployment candidates: Amazon ECS/Fargate or AWS App Runner.
- Observability: CloudWatch-compatible container logs.
- Repository: https://github.com/Rehan9599/opencv-ai-competition-Sonar-project

The full Django/Postgres/Redis dashboard remains useful for local demonstration. The AWS
path stays deliberately focused on the edge service so the contest deployment does not
require reproducing the entire local application stack.

## Evidence to collect

- OpenCV, NumPy, and ONNX Runtime versions from `/health`.
- Model filename, SHA-256, class list, and inference provider.
- Separate OpenCV preprocessing and neural inference timings.
- Detection JSON and annotated output for shipwreck, pipeline, mine, ghost-net, and empty-seabed samples.
- AWS endpoint response, S3 result object, and CloudWatch log entry.
- Container build and smoke-test output.

## Responsible-use limitations

- Ghost-net performance is synthetic capability evidence unless independently validated.
- Shipwreck site-disjointness is not fully audited.
- Geolocation includes uncertainty and should be treated as a search area.
- Detections require human review.
- Results are not enforcement evidence by themselves.
- Dataset and model licenses must be verified before publication.

## Submission materials

- Technical report covering OpenCV 5, AWS architecture, evaluation, latency, cost, failure cases, licenses, and responsible use.
- Demonstration video under five minutes.
- Public repository and reproducibility commands.
- Live AWS endpoint or a reliable live screen-share fallback.
- Accurate Devpost technology list, screenshots, credits, and links.
