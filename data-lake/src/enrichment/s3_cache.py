import json

import boto3
from botocore.exceptions import ClientError

BUCKET = "taller4-datalake-sebasgiraldo69"
REGION = "us-east-1"

CACHE_PREFIX = "cache/comprehend/v1/"


def cache_key_path(cache_key):
    return f"{CACHE_PREFIX}{cache_key}.json"


def load_s3_cache(cache_key, s3_client=None):
    """Consulta un resultado previamente procesado."""
    s3 = s3_client or boto3.client(
        "s3", region_name=REGION
    )

    try:
        response = s3.get_object(
            Bucket=BUCKET,
            Key=cache_key_path(cache_key),
        )

        return json.loads(response["Body"].read())

    except ClientError as error:
        code = error.response["Error"]["Code"]

        if code in ("NoSuchKey", "404"):
            return None

        raise


def save_s3_cache(cache_key, result, s3_client=None):
    """Guarda un resultado real de Comprehend."""
    if result.get("status") != "processed":
        raise ValueError(
            "Solo se permiten resultados procesados"
        )

    s3 = s3_client or boto3.client(
        "s3", region_name=REGION
    )

    s3.put_object(
        Bucket=BUCKET,
        Key=cache_key_path(cache_key),
        Body=json.dumps(
            result,
            ensure_ascii=False,
        ).encode("utf-8"),
        ContentType="application/json",
        ServerSideEncryption="AES256",
    )
