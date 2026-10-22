
import hashlib
import json
import xml.etree.ElementTree as ET

import boto3

BUCKET = "taller4-datalake-sebasgiraldo69"
s3 = boto3.client("s3", region_name="us-east-1")


def validate_bronze():
    paginator = s3.get_paginator("list_objects_v2")

    total = 0
    valid = 0
    invalid = 0

    for page in paginator.paginate(
        Bucket=BUCKET,
        Prefix="bronze/source=eltiempo/"
    ):
        for obj in page.get("Contents", []):
            key = obj["Key"]

            if not key.endswith("metadata.json"):
                continue

            total += 1

            try:
                response = s3.get_object(
                    Bucket=BUCKET,
                    Key=key
                )

                metadata = json.loads(
                    response["Body"].read()
                )

                xml_location = metadata["s3_location"]
                prefix = f"s3://{BUCKET}/"

                if not xml_location.startswith(prefix):
                    raise ValueError("Ubicación S3 inválida")

                xml_key = xml_location[len(prefix):]

                xml_response = s3.get_object(
                    Bucket=BUCKET,
                    Key=xml_key
                )

                xml_bytes = xml_response["Body"].read()

                calculated_hash = hashlib.sha256(
                    xml_bytes
                ).hexdigest()

                if calculated_hash != metadata["sha256"]:
                    raise ValueError("Hash SHA-256 diferente")

                root = ET.fromstring(xml_bytes)

                if root.tag != "rss":
                    raise ValueError("No es un documento RSS")

                news = root.findall("./channel/item")

                if not news:
                    raise ValueError("RSS sin noticias")

                valid += 1

                print(
                    f"VALIDO | {metadata['section']} | "
                    f"{len(news)} noticias | "
                    f"{metadata.get('status', 'initial')}"
                )

            except Exception as error:
                invalid += 1
                print(f"INVALIDO | {key} | {error}")

    print("\nRESUMEN VALIDACION BRONZE")
    print(f"Total de registros: {total}")
    print(f"Validos: {valid}")
    print(f"Invalidos: {invalid}")

    if invalid:
        raise SystemExit(1)


if __name__ == "__main__":
    validate_bronze()
