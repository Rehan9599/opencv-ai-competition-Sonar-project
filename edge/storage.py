"""Optional S3 result storage for the contest inference service."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from uuid import uuid4


def is_enabled() -> bool:
    return bool(os.environ.get("DRISHTI_S3_BUCKET"))


def store_result(result: dict) -> str | None:
    """Store one JSON result when a bucket is configured, otherwise do nothing."""
    bucket = os.environ.get("DRISHTI_S3_BUCKET")
    if not bucket:
        return None

    import boto3

    prefix = os.environ.get("DRISHTI_S3_PREFIX", "drishti/results").strip("/")
    timestamp = datetime.now(timezone.utc).strftime("%Y/%m/%d")
    key = f"{prefix}/{timestamp}/{uuid4().hex}.json"
    body = json.dumps(result, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    client = boto3.client("s3", region_name=os.environ.get("AWS_REGION"))
    client.put_object(
        Bucket=bucket,
        Key=key,
        Body=body,
        ContentType="application/json",
        ServerSideEncryption="AES256",
    )
    return f"s3://{bucket}/{key}"
