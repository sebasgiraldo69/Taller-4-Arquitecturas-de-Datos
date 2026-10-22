import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

import boto3
import requests
import yaml
from botocore.exceptions import ClientError, BotoCoreError

BASE_DIR = Path(__file__).resolve().parents[2]
CONFIG_PATH = BASE_DIR / "config" / "rss_sources.yaml"

BUCKET = "taller4-datalake-sebasgiraldo69"
REGION = "us-east-1"


def find_existing_xml(s3, section, content_hash):
    """Busca un XML con el mismo hash en la sección."""
    prefix = f"bronze/source=eltiempo/section={section}/"
    paginator = s3.get_paginator("list_objects_v2")

    for page in paginator.paginate(Bucket=BUCKET, Prefix=prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]

            if not key.endswith("/metadata.json"):
                continue

            result = s3.get_object(Bucket=BUCKET, Key=key)
            metadata = json.loads(result["Body"].read())

            if (
                metadata.get("sha256") == content_hash
                and metadata.get("s3_location")
                and metadata.get("status") != "duplicate"
            ):
                return metadata["s3_location"]

    return None


def main():
    with open(CONFIG_PATH, encoding="utf-8") as file:
        config = yaml.safe_load(file)

    s3 = boto3.client("s3", region_name=REGION)
    run_id = str(uuid.uuid4())

    print(f"Inicio de ingesta Bronze: {run_id}")

    for source in config["sources"]:
        section = source["section"]
        url = source["url"]

        print(f"\nProcesando: {section}")

        try:
            response = requests.get(
                url,
                timeout=30,
                headers={"User-Agent": "Taller4DataLake/1.0"},
            )
            response.raise_for_status()

            xml_bytes = response.content
            ingestion_time = datetime.now(timezone.utc)
            content_hash = hashlib.sha256(xml_bytes).hexdigest()

            prefix = (
                f"bronze/source=eltiempo/"
                f"section={section}/"
                f"year={ingestion_time:%Y}/"
                f"month={ingestion_time:%m}/"
                f"day={ingestion_time:%d}/"
                f"run_id={run_id}"
            )

            xml_key = f"{prefix}/feed.xml"
            metadata_key = f"{prefix}/metadata.json"

            existing_xml = find_existing_xml(
                s3, section, content_hash
            )

            if existing_xml:
                status = "duplicate"
                s3_location = existing_xml
                print("Contenido repetido. No se guarda otro XML.")
            else:
                status = "new"
                s3_location = f"s3://{BUCKET}/{xml_key}"

                s3.put_object(
                    Bucket=BUCKET,
                    Key=xml_key,
                    Body=xml_bytes,
                    ContentType="application/xml",
                )
                print(f"Nuevo XML guardado: {s3_location}")

            metadata = {
                "run_id": run_id,
                "source": source["media"],
                "section": section,
                "source_url": url,
                "ingestion_timestamp_utc": ingestion_time.isoformat(),
                "http_status": response.status_code,
                "sha256": content_hash,
                "s3_location": s3_location,
                "size_bytes": len(xml_bytes),
                "status": status,
            }

            s3.put_object(
                Bucket=BUCKET,
                Key=metadata_key,
                Body=json.dumps(
                    metadata,
                    ensure_ascii=False,
                    indent=2,
                ).encode("utf-8"),
                ContentType="application/json",
            )

            print(f"Estado: {status}")
            print(f"SHA256: {content_hash}")

        except (
            requests.RequestException,
            ClientError,
            BotoCoreError,
        ) as error:
            print(f"Error procesando {section}: {error}")
            raise

    print("\nIngesta Bronze finalizada correctamente.")


if __name__ == "__main__":
    main()
