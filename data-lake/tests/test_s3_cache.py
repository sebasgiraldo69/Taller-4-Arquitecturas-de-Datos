import importlib.util
import io
import json
from pathlib import Path

import pytest
from botocore.exceptions import ClientError

MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "enrichment"
    / "s3_cache.py"
)

spec = importlib.util.spec_from_file_location(
    "s3_cache", MODULE_PATH
)

module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class FakeS3:
    def __init__(self):
        self.objects = {}

    def put_object(self, Bucket, Key, Body, **kwargs):
        self.objects[(Bucket, Key)] = Body

    def get_object(self, Bucket, Key):
        value = self.objects.get((Bucket, Key))

        if value is None:
            raise ClientError(
                {
                    "Error": {
                        "Code": "NoSuchKey",
                        "Message": "Not found",
                    }
                },
                "GetObject",
            )

        return {"Body": io.BytesIO(value)}


def test_cache_miss():
    fake = FakeS3()

    result = module.load_s3_cache(
        "hash-inexistente",
        s3_client=fake,
    )

    assert result is None


def test_cache_round_trip():
    fake = FakeS3()

    original = {
        "entities": [
            {
                "text": "Microsoft",
                "type": "ORGANIZATION",
                "score": 0.99,
            }
        ],
        "key_phrases": [],
        "status": "processed",
    }

    module.save_s3_cache(
        "hash-prueba",
        original,
        s3_client=fake,
    )

    recovered = module.load_s3_cache(
        "hash-prueba",
        s3_client=fake,
    )

    assert recovered == original


def test_reject_unprocessed_cache():
    fake = FakeS3()

    with pytest.raises(ValueError):
        module.save_s3_cache(
            "hash-prueba",
            {"status": "not_processed"},
            s3_client=fake,
        )
