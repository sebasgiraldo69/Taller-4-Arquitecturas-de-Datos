import hashlib
import json
import re
import xml.etree.ElementTree as ET
from collections import Counter
from urllib.parse import urlsplit, urlunsplit

import boto3
from bs4 import BeautifulSoup

BUCKET = "taller4-datalake-sebasgiraldo69"
REGION = "us-east-1"

s3 = boto3.client("s3", region_name=REGION)


def clean_text(value):
    if not value:
        return ""

    text = BeautifulSoup(
        value, "html.parser"
    ).get_text(" ")

    return re.sub(r"\s+", " ", text).strip()


def normalize_url(value):
    parts = urlsplit((value or "").strip())

    return urlunsplit((
        parts.scheme.lower(),
        parts.netloc.lower(),
        parts.path.rstrip("/") or "/",
        "",
        "",
    ))


def get_text(item, tag):
    element = item.find(tag)

    if element is None:
        return ""

    return element.text or ""


def load_bronze_snapshots():
    """Obtiene las noticias de cada captura histórica."""
    snapshots = []

    paginator = s3.get_paginator("list_objects_v2")

    for page in paginator.paginate(
        Bucket=BUCKET,
        Prefix="bronze/source=eltiempo/",
    ):
        for obj in page.get("Contents", []):
            key = obj["Key"]

            if not key.endswith("/metadata.json"):
                continue

            response = s3.get_object(
                Bucket=BUCKET,
                Key=key,
            )

            metadata = json.loads(
                response["Body"].read()
            )

            xml_location = metadata["s3_location"]
            expected_prefix = f"s3://{BUCKET}/"

            if not xml_location.startswith(expected_prefix):
                raise ValueError(
                    f"Ubicación S3 inválida: {xml_location}"
                )

            xml_key = xml_location[len(expected_prefix):]

            xml_response = s3.get_object(
                Bucket=BUCKET,
                Key=xml_key,
            )

            xml_bytes = xml_response["Body"].read()

            actual_hash = hashlib.sha256(
                xml_bytes
            ).hexdigest()

            if actual_hash != metadata["sha256"]:
                raise ValueError(
                    f"Hash inválido: {xml_key}"
                )

            root = ET.fromstring(xml_bytes)
            news = []

            for item in root.findall("./channel/item"):
                title = clean_text(
                    get_text(item, "title")
                )

                description = clean_text(
                    get_text(item, "description")
                )

                url = normalize_url(
                    get_text(item, "link")
                )

                if not title or not url:
                    continue

                news_id = hashlib.sha256(
                    url.encode("utf-8")
                ).hexdigest()

                content_hash = hashlib.sha256(
                    f"{title}|{description}".encode("utf-8")
                ).hexdigest()

                news.append({
                    "news_id": news_id,
                    "title": title,
                    "section": metadata["section"],
                    "content_hash": content_hash,
                })

            snapshots.append({
                "run_id": metadata["run_id"],
                "section": metadata["section"],
                "ingested_at":
                    metadata["ingestion_timestamp_utc"],
                "news": news,
            })

    return sorted(
        snapshots,
        key=lambda x: (
            x["ingested_at"],
            x["run_id"],
            x["section"],
        ),
    )


def detect_changes(snapshots):
    """Compara cada noticia con su última versión conocida."""
    previous = {}
    changes = []

    for snapshot in snapshots:
        for news in snapshot["news"]:
            news_id = news["news_id"]
            current_hash = news["content_hash"]

            if news_id not in previous:
                status = "new"
            elif previous[news_id] != current_hash:
                status = "updated"
            else:
                status = "unchanged"

            changes.append({
                "run_id": snapshot["run_id"],
                "section": news["section"],
                "news_id": news_id,
                "title": news["title"],
                "status": status,
                "content_hash": current_hash,
            })

            previous[news_id] = current_hash

    return changes


def main():
    snapshots = load_bronze_snapshots()
    changes = detect_changes(snapshots)

    counts = Counter(
        change["status"] for change in changes
    )

    print("\nDETECCIÓN DE CAMBIOS EN NOTICIAS")
    print(f"Capturas procesadas: {len(snapshots)}")
    print(f"Noticias evaluadas: {len(changes)}")
    print(f"Nuevas: {counts['new']}")
    print(f"Actualizadas: {counts['updated']}")
    print(f"Sin cambios: {counts['unchanged']}")

    print("\nDETALLE DE ACTUALIZACIONES")

    updated = [
        change for change in changes
        if change["status"] == "updated"
    ]

    if not updated:
        print("No se detectaron actualizaciones.")
    else:
        for change in updated:
            print(
                f"- [{change['section']}] "
                f"{change['title']}"
            )

    print("\nAnálisis finalizado correctamente.")


if __name__ == "__main__":
    main()
