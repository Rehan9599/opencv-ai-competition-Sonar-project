# AWS Console Runbook — ECS Express Mode

This deploys the CPU inference API and single-image upload UI from `edge/` using **Amazon ECS
Express Mode on Fargate**.

## 1. Pick a region and create a budget

Use `us-east-1` for the existing ECR repository, ECS service, S3 bucket, and CloudWatch logs.
Create a monthly cost budget with email alerts at 80% and 100% of the cap you choose.

## 2. Create the ECR repository in the console

In **Amazon ECR → Private registry → Repositories → Create repository**:

- Repository name: `drishti-9599`
- Visibility: private
- Enable scan on push
- Enable immutable tags if offered

Copy the AWS account ID and note the region. The image will be pushed from the local machine;
the ECR console does not upload a local Docker image.

## 3. Authenticate locally and push the built image

Install AWS CLI v2 and Docker Desktop. With console credentials, AWS CLI 2.32 or newer can
authenticate through a browser using `aws login --profile drishti-contest`; IAM Identity Center
users should use `aws configure sso --profile drishti-contest` and `aws sso login` instead.
Do not create or paste long-lived access keys.

Run this in PowerShell from the repository root after signing in:

```powershell
$Region = "us-east-1"
$AccountId = "563691829406"
$Repo = "drishti-9599"
$Tag = "contest-frontend-1"
$Registry = "$AccountId.dkr.ecr.$Region.amazonaws.com"

aws sts get-caller-identity --profile drishti-contest
aws ecr get-login-password --region $Region --profile drishti-contest |
  docker login --username AWS --password-stdin $Registry
docker build -f edge/Dockerfile.edge -t drishti-edge:frontend-1 .
docker tag drishti-edge:frontend-1 "${Registry}/${Repo}:${Tag}"
docker push "${Registry}/${Repo}:${Tag}"
```

In ECR, verify the `contest-frontend-1` image appears and copy its digest.

## 4. Create the result bucket and retention rule

In **Amazon S3 → Create bucket**:

- Bucket name: `drishti95-bucket`.
- Region: `us-east-1`.
- Keep **Block all public access** enabled.
- Keep default encryption enabled (SSE-S3); leave versioning off for this demo.

Under **Management → Create lifecycle rule**, filter by prefix `drishti/results/` and expire
objects after 30 days.

## 5. Create the S3 task role

In **IAM → Roles → Create role → AWS service → Elastic Container Service → ECS Task**, create
`drishti-edge-task-role`. Add this inline permission, replacing the bucket name:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["s3:PutObject"],
    "Resource": "arn:aws:s3:::drishti95-bucket/drishti/results/*"
  }]
}
```

The application only writes JSON results. It does not need bucket listing or read access.

## 6. Create the public ECS Express Mode service

In **Amazon ECS → Express mode**, browse to the private ECR repository and select the image
digest you copied. For **Task execution role** and **Infrastructure role**, use the console's
**Create new role** choices if these roles do not already exist. In **Additional configurations**,
set:

- Service name: `drishti-edge`
- Container port: `8100`
- Health check path: `/health`
- Task role: `drishti-edge-task-role`
- CPU/memory: start at 1 vCPU / 2 GB
- Minimum and maximum tasks: 1 and 1 for the demo
- Public HTTPS URL: enabled
- CloudWatch logging: enabled

Add these environment variables:

```text
DRISHTI_ONNX=/app/ml/models/exported/best_detector.onnx
DRISHTI_CALIBRATOR=/app/ml/models/exported/calibrator.pkl
DRISHTI_PREPROCESS=1
DRISHTI_MAX_UPLOAD_BYTES=10485760
DRISHTI_S3_BUCKET=drishti95-bucket
DRISHTI_S3_PREFIX=drishti/results
AWS_REGION=us-east-1
```

Review the resources and choose **Create**. Wait for deployment to finish and the service to
become healthy.

## 7. Verify and capture evidence

Open the service's Application URL in Chrome to use the upload interface at `/`. The page
shows the active ONNX model, OpenCV version, provider, and model hash. You can also open
`/health` directly and confirm `status` is `ok`, OpenCV is `5.0.0`, and
`s3_result_storage` is `true`.

Use the browser upload form to choose a PNG/JPEG and run detection. Or submit a sample image
from PowerShell:

```powershell
$ServiceUrl = "https://<application-url>"
curl.exe --fail "$ServiceUrl/health"
curl.exe --fail -F "file=@demo/frontend_test/02_shipwreck.jpg" "$ServiceUrl/detect"
```

The detection response should contain a `result_uri`. Verify the JSON object under
`drishti/results/` in S3 and the request/startup logs in CloudWatch. Capture the URL, health JSON,
detection JSON, S3 object, and CloudWatch log for the submission.

The endpoint accepts unauthenticated image uploads. Keep the 10 MB upload limit and one-task
scale cap; delete the service after the contest demo if it is no longer needed. ECS Express Mode
has no extra service fee, but its Fargate tasks, load balancer, logs, and data transfer are billed.

For an account-created infrastructure role, ECS Express Mode's managed policy may need the two
supplemental inline policies in `deploy/aws/iam/` (tag-scoped ALB creation and read-only VPC
discovery). This account required them during provisioning; attach them if CloudTrail reports
those specific `AccessDenied` actions.
