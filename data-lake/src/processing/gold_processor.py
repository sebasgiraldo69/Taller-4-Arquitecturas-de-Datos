
import io
import json
from datetime import datetime, timezone
from uuid import uuid4

import boto3
import pandas as pd


BUCKET = "taller4-datalake-sebasgiraldo69"
REGION = "us-east-1"

s3 = boto3.client("s3", region_name=REGION)


def latest_object(prefix, suffix):
    paginator = s3.get_paginator("list_objects_v2")
    objects = []

    for page in paginator.paginate(
        Bucket=BUCKET,
        Prefix=prefix,
    ):
        for obj in page.get("Contents", []):
            if obj["Key"].endswith(suffix):
                objects.append(obj)

    if not objects:
        raise FileNotFoundError(
            f"No se encontraron archivos en {prefix}"
        )

    return max(
        objects,
        key=lambda obj: obj["LastModified"],
    )["Key"]


def read_json(key):
    response = s3.get_object(
        Bucket=BUCKET,
        Key=key,
    )
    return json.loads(response["Body"].read())


def read_parquet(key):
    response = s3.get_object(
        Bucket=BUCKET,
        Key=key,
    )
    return pd.read_parquet(
        io.BytesIO(response["Body"].read())
    )


def s3_key_from_uri(uri):
    prefix = f"s3://{BUCKET}/"

    if not uri.startswith(prefix):
        raise ValueError(f"Ruta S3 inesperada: {uri}")

    return uri[len(prefix):]


def save_parquet(df, key):
    buffer = io.BytesIO()

    df.to_parquet(
        buffer,
        index=False,
        engine="pyarrow",
    )

    s3.put_object(
        Bucket=BUCKET,
        Key=key,
        Body=buffer.getvalue(),
        ContentType="application/octet-stream",
        ServerSideEncryption="AES256",
    )


def save_json(data, key):
    s3.put_object(
        Bucket=BUCKET,
        Key=key,
        Body=json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
        ).encode("utf-8"),
        ContentType="application/json",
        ServerSideEncryption="AES256",
    )


def main():
    print("\nPROCESAMIENTO GOLD")

    # 1. Leer publicación Silver completada
    manifest_key = latest_object(
        "silver/publications/",
        "/manifest.json",
    )

    silver_manifest = read_json(manifest_key)

    if silver_manifest.get("status") != "completed":
        raise ValueError(
            "La publicación Silver no está completada."
        )

    news_key = s3_key_from_uri(
        silver_manifest["source_news"]
    )

    entities_key = s3_key_from_uri(
        silver_manifest["entities_path"]
    )

    phrases_key = s3_key_from_uri(
        silver_manifest["key_phrases_path"]
    )

    news = read_parquet(news_key)
    entities = read_parquet(entities_key)
    phrases = read_parquet(phrases_key)

    # 2. Verificaciones básicas
    if len(news) != silver_manifest["news_count"]:
        raise ValueError(
            "Cantidad de noticias diferente al manifiesto."
        )

    if len(entities) != silver_manifest["entities_count"]:
        raise ValueError(
            "Cantidad de entidades diferente al manifiesto."
        )

    if len(phrases) != silver_manifest["key_phrases_count"]:
        raise ValueError(
            "Cantidad de frases diferente al manifiesto."
        )

    if not news["news_id"].is_unique:
        raise ValueError("Existen noticias duplicadas.")

    print(f"Publicación Silver: {silver_manifest['publication_id']}")
    print(f"Noticias: {len(news)}")
    print(f"Entidades: {len(entities)}")
    print(f"Frases clave: {len(phrases)}")

    # 3. Preparar datos de noticias
    required = {"news_id", "section", "published_at"}

    missing = required - set(news.columns)

    if missing:
        raise ValueError(
            f"Faltan columnas en news.parquet: {sorted(missing)}"
        )

    news = news.copy()

    news["published_at"] = pd.to_datetime(
        news["published_at"],
        errors="coerce",
        utc=True,
    )

    if news["published_at"].isna().any():
        raise ValueError(
            "Existen noticias sin fecha de publicación válida."
        )

    news["publication_date"] = (
        news["published_at"].dt.strftime("%Y-%m-%d")
    )

    # 4. Gold: resumen de noticias
    news_summary = (
        news.groupby(
            ["publication_date", "section"],
            dropna=False,
        )
        .agg(
            news_count=("news_id", "nunique")
        )
        .reset_index()
    )

    # 5. Gold: entidades frecuentes
    entity_news = entities.merge(
        news[["news_id", "section"]],
        on="news_id",
        how="inner",
        validate="many_to_one",
    )

    top_entities = (
        entity_news.groupby(
            ["section", "entity_type", "entity_text"],
            dropna=False,
        )
        .agg(
            mentions=("news_id", "size"),
            news_count=("news_id", "nunique"),
            avg_score=("score", "mean"),
        )
        .reset_index()
        .sort_values(
            ["section", "mentions"],
            ascending=[True, False],
        )
    )

    # 6. Gold: frases clave frecuentes
    phrase_news = phrases.merge(
        news[["news_id", "section"]],
        on="news_id",
        how="inner",
        validate="many_to_one",
    )

    top_key_phrases = (
        phrase_news.groupby(
            ["section", "phrase_text"],
            dropna=False,
        )
        .agg(
            mentions=("news_id", "size"),
            news_count=("news_id", "nunique"),
            avg_score=("score", "mean"),
        )
        .reset_index()
        .sort_values(
            ["section", "mentions"],
            ascending=[True, False],
        )
    )

    # 7. Publicar Gold con identificador único
    now = datetime.now(timezone.utc)
    run_id = uuid4().hex

    partition = (
        f"year={now:%Y}/"
        f"month={now:%m}/"
        f"day={now:%d}/"
        f"run_id={run_id}"
    )

    tables = {
        "news_summary": news_summary,
        "top_entities": top_entities,
        "top_key_phrases": top_key_phrases,
    }

    paths = {}

    for name, df in tables.items():
        key = (
            f"gold/{name}/{partition}/{name}.parquet"
        )

        save_parquet(df, key)
        paths[name] = f"s3://{BUCKET}/{key}"

        print(f"\n{name}: {len(df)} filas")
        print(paths[name])

    # 8. Publicar manifiesto Gold al final
    manifest = {
        "status": "completed",
        "run_id": run_id,
        "created_at_utc": now.isoformat(),
        "source_silver_publication_id": (
            silver_manifest["publication_id"]
        ),
        "source_silver_manifest": (
            f"s3://{BUCKET}/{manifest_key}"
        ),
        "tables": paths,
        "row_counts": {
            name: len(df)
            for name, df in tables.items()
        },
    }

    manifest_output_key = (
        f"gold/publications/{partition}/manifest.json"
    )

    save_json(manifest, manifest_output_key)

    print("\nPUBLICACIÓN GOLD COMPLETADA")
    print(f"Run ID: {run_id}")
    print(
        f"Manifest: s3://{BUCKET}/{manifest_output_key}"
    )


if __name__ == "__main__":
    main()
