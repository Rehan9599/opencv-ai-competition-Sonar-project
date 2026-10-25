# AWS Deployment Runbook

This deployment exposes only the CPU inference service in `edge/`. The Django/Postgres/Redis
stack remains the richer local demonstration.

## Required AWS resources

- ECR repository for the edge image
- App Runner service or ECS Fargate service
- S3 bucket for JSON result objects
- Task/service IAM role with `s3:PutObject` only on the result prefix
- CloudWatch log group
- Budget alert and an S3 lifecycle rule

## Build and publish the image

Set these values in your shell, not in the repository:

```bash
export AWS_REGION=us-east-1
export AWS_ACCOUNT_ID=000000000000
export ECR_REPOSITORY=drishti-edge
export IMAGE_TAG=contest-2026

aws ecr create-repository \
  --repository-name "$ECR_REPOSITORY" \
  --region "$AWS_REGION"

aws ecr get-login-password --region "$AWS_REGION" |
  docker login --username AWS --password-stdin \
  "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"

docker build -f edge/Dockerfile.edge \
  -t "$ECR_REPOSITORY:$IMAGE_TAG" .

docker tag "$ECR_REPOSITORY:$IMAGE_TAG" \
  "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:$IMAGE_TAG"

docker push \
  "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:$IMAGE_TAG"
```

## Container configuration

Set these environment variables in App Runner or the ECS task definition:

```text
DRISHTI_ONNX=/app/ml/models/exported/best_detector.onnx
DRISHTI_CALIBRATOR=/app/ml/models/exported/calibrator.pkl
DRISHTI_PREPROCESS=1
DRISHTI_MAX_UPLOAD_BYTES=10485760
DRISHTI_S3_BUCKET=<private-result-bucket>
DRISHTI_S3_PREFIX=drishti/results
AWS_REGION=<region>
```

Do not add AWS access keys. App Runner or ECS should use an instance/task role.

## Minimal S3 policy

Replace the placeholders before creating the role policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:PutObject"],
      "Resource": "arn:aws:s3:::<private-result-bucket>/drishti/results/*"
    }
  ]
}
```

If uploaded source images are added later, grant a separate, explicit prefix rather than
broadening this policy to the whole bucket.

## Smoke test

```bash
export SERVICE_URL=https://<service-hostname>
curl --fail "$SERVICE_URL/health"
curl --fail \
  -F "file=@demo/frontend_test/02_shipwreck.jpg" \
  "$SERVICE_URL/detect"
```

Record the health response, HTTP latency, detection JSON, S3 object URI, and CloudWatch log
entry in the contest evidence log. Do not publish a public endpoint until upload limits,
S3 permissions, logs, and the budget alert are verified.
