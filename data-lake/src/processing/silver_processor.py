import hashlib
import io
import json
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlsplit, urlunsplit
import xml.etree.ElementTree as ET

from news_change_detector import (
    load_bronze_snapshots,
    detect_changes,
)

import boto3
import pandas as pd
from bs4 import BeautifulSoup

BUCKET = "taller4-datalake-sebasgiraldo69"
REGION = "us-east-1"

s3 = boto3.client("s3", region_name=REGION)


def clean_text(value):
    """Elimina etiquetas HTML y espacios innecesarios."""
    if not value:
        return ""

    text = BeautifulSoup(value, "html.parser").get_text(" ")
    return re.sub(r"\s+", " ", text).strip()


def normalize_url(value):
    """Normaliza la URL para identificar noticias repetidas."""
    value = (value or "").strip()
    parts = urlsplit(value)

    return urlunsplit((
        parts.scheme.lower(),
        parts.netloc.lower(),
        parts.path.rstrip("/") or "/",
        "",
        "",
    ))


def get_text(item, tag):
    """Obtiene el contenido de una etiqueta XML."""
    element = item.find(tag)

    if element is None:
        return ""

    return element.text or ""


def parse_date(value):
    """Convierte fechas RSS a timestamps UTC."""
    if not value:
        return pd.NaT

    try:
        parsed = parsedate_to_datetime(value)
        return pd.to_datetime(parsed, utc=True)
    except (ValueError, TypeError, OverflowError):
        try:
            return pd.to_datetime(value, utc=True, errors="coerce")
        except (ValueError, TypeError, OverflowError):
            return pd.NaT


def read_bronze_news():
    """Lee y transforma las noticias almacenadas en Bronze."""
    records = []
    rejected = []

    paginator = s3.get_paginator("list_objects_v2")

    for page in paginator.paginate(
        Bucket=BUCKET,
        Prefix="bronze/source=eltiempo/",
    ):
        for obj in page.get("Contents", []):
            key = obj["Key"]

            if not key.endswith("metadata.json"):
                continue

            metadata_object = s3.get_object(
                Bucket=BUCKET,
                Key=key,
            )

            metadata = json.loads(
                metadata_object["Body"].read()
            )

            xml_location = metadata["s3_location"]
            prefix = f"s3://{BUCKET}/"

            if not xml_location.startswith(prefix):
                raise ValueError(
                    f"Ubicación Bronze inválida: {xml_location}"
                )

            xml_key = xml_location[len(prefix):]

            xml_object = s3.get_object(
                Bucket=BUCKET,
                Key=xml_key,
            )

            xml_bytes = xml_object["Body"].read()

            actual_hash = hashlib.sha256(
                xml_bytes
            ).hexdigest()

            if actual_hash != metadata["sha256"]:
                raise ValueError(
                    f"Hash inválido para {xml_key}"
                )

            root = ET.fromstring(xml_bytes)

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

                published = parse_date(
                    get_text(item, "pubDate")
                )

                if not title or not url:
                    rejected.append({
                        "section": metadata["section"],
                        "title": title,
                        "url": url,
                        "reason": "missing_title_or_url",
                        "run_id": metadata["run_id"],
                    })
                    continue

                news_id = hashlib.sha256(
                    url.encode("utf-8")
                ).hexdigest()

                content_hash = hashlib.sha256(
                    f"{title}|{description}".encode("utf-8")
                ).hexdigest()

                records.append({
                    "news_id": news_id,
                    "title": title,
                    "description": description,
                    "url": url,
                    "section": metadata["section"],
                    "source": metadata["source"],
                    "published_at": published,
                    "content_hash": content_hash,
                    "ingestion_timestamp_utc":
                        metadata["ingestion_timestamp_utc"],
                })

    return records, rejected


def main():
    records, rejected = read_bronze_news()

    if not records:
        raise ValueError(
            "No se encontraron noticias válidas en Bronze."
        )

    df = pd.DataFrame(records)

    # Normalizar fechas a UTC
    df["published_at"] = pd.to_datetime(
        df["published_at"],
        utc=True,
        errors="coerce",
    )

    df["ingestion_timestamp_utc"] = pd.to_datetime(
        df["ingestion_timestamp_utc"],
        utc=True,
        errors="coerce",
    )

    # Conservar la última versión por noticia
    df = df.sort_values(
        "ingestion_timestamp_utc",
        kind="stable",
    )

    before = len(df)

    df = df.drop_duplicates(
        subset=["news_id"],
        keep="last",
    )

    # Fecha de procesamiento para particionar Silver
    now = datetime.now(timezone.utc)

    df["year"] = now.year
    df["month"] = now.month
    df["day"] = now.day

    # Generar archivo Parquet
    buffer = io.BytesIO()

    df.to_parquet(
        buffer,
        index=False,
        engine="pyarrow",
    )

    silver_key = (
        f"silver/news/year={now:%Y}/"
        f"month={now:%m}/"
        f"day={now:%d}/news.parquet"
    )

    s3.put_object(
        Bucket=BUCKET,
        Key=silver_key,
        Body=buffer.getvalue(),
        ContentType="application/octet-stream",
    )

    print("\nPROCESAMIENTO SILVER")
    print(f"Registros leídos: {before}")
    print(f"Noticias únicas: {len(df)}")
    print(f"Duplicados eliminados: {before - len(df)}")
    print(f"Registros rechazados: {len(rejected)}")
    print(f"Parquet: s3://{BUCKET}/{silver_key}")

    # Almacenar registros rechazados
    if rejected:
        quarantine_key = (
            f"quarantine/news/"
            f"year={now:%Y}/"
            f"month={now:%m}/"
            f"day={now:%d}/rejected.json"
        )

        s3.put_object(
            Bucket=BUCKET,
            Key=quarantine_key,
            Body=json.dumps(
                rejected,
                ensure_ascii=False,
                indent=2,
            ).encode("utf-8"),
            ContentType="application/json",
        )

        print(
            f"Cuarentena: s3://{BUCKET}/{quarantine_key}"
        )


    # Reconstruir historial de cambios desde Bronze
    snapshots = load_bronze_snapshots()
    changes = detect_changes(snapshots)

    changes_df = pd.DataFrame(changes)

    if not changes_df.empty:
        changes_df["ingestion_timestamp_utc"] = pd.to_datetime(
            changes_df["ingestion_timestamp_utc"],
            utc=True,
        )

        changes_df = changes_df.sort_values(
            ["ingestion_timestamp_utc", "run_id", "news_id"],
            kind="stable",
        )

        changes_buffer = io.BytesIO()

        changes_df.to_parquet(
            changes_buffer,
            index=False,
            engine="pyarrow",
        )

        changes_key = (
            f"silver/news_changes/year={now:%Y}/"
            f"month={now:%m}/"
            f"day={now:%d}/news_changes.parquet"
        )

        s3.put_object(
            Bucket=BUCKET,
            Key=changes_key,
            Body=changes_buffer.getvalue(),
            ContentType="application/octet-stream",
        )

        print("\nHISTORIAL DE CAMBIOS")
        print(f"Registros: {len(changes_df)}")
        print(changes_df["status"].value_counts())
        print(f"Parquet: s3://{BUCKET}/{changes_key}")

    print("\nProcesamiento Silver finalizado correctamente.")


if __name__ == "__main__":
    main()
