import argparse
import io
import json
from collections import Counter
from datetime import datetime, timezone
from uuid import uuid4

import boto3
import pandas as pd

from comprehend_enrichment import enrich_news
from enrichment_tables import build_enrichment_tables


BUCKET = "taller4-datalake-sebasgiraldo69"
REGION = "us-east-1"

s3 = boto3.client("s3", region_name=REGION)


def load_news():
    """Carga el archivo news.parquet más reciente desde S3."""
    paginator = s3.get_paginator("list_objects_v2")
    files = []

    for page in paginator.paginate(
        Bucket=BUCKET,
        Prefix="silver/news/",
    ):
        for obj in page.get("Contents", []):
            key = obj["Key"]

            if key.endswith("/news.parquet"):
                files.append((obj["LastModified"], key))

    if not files:
        raise ValueError(
            "No se encontró news.parquet en Silver."
        )

    _, latest_key = max(files)

    response = s3.get_object(
        Bucket=BUCKET,
        Key=latest_key,
    )

    df = pd.read_parquet(
        io.BytesIO(response["Body"].read())
    )

    return df, latest_key


def save_parquet(df, key):
    """Guarda un DataFrame en formato Parquet en S3."""
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
    """Guarda un documento JSON en S3."""
    body = json.dumps(
        data,
        ensure_ascii=False,
        indent=2,
        default=str,
    ).encode("utf-8")

    s3.put_object(
        Bucket=BUCKET,
        Key=key,
        Body=body,
        ContentType="application/json",
        ServerSideEncryption="AES256",
    )


def can_publish(total_news, selected_news, pending_news):
    """
    Publica solamente cuando se procesaron
    todas las noticias disponibles.
    """
    return (
        total_news > 0
        and selected_news == total_news
        and pending_news == 0
    )


def main():
    parser = argparse.ArgumentParser(
        description="Enriquecimiento Silver con Amazon Comprehend"
    )

    parser.add_argument(
        "--allow-api-calls",
        action="store_true",
        help="Autoriza llamadas reales a Amazon Comprehend",
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Número máximo de noticias a procesar",
    )

    parser.add_argument(
        "--offset",
        type=int,
        default=0,
        help="Número de noticias que se omiten al inicio",
    )

    args = parser.parse_args()

    if args.offset < 0:
        parser.error("--offset no puede ser negativo")

    if args.limit is not None and args.limit < 1:
        parser.error("--limit debe ser mayor que cero")

    # 1. Cargar todas las noticias
    all_news_df, source_key = load_news()

    all_news_df = all_news_df.sort_values(
        by="news_id",
        kind="stable",
    ).reset_index(drop=True)

    total_news = len(all_news_df)

    # 2. Seleccionar lote
    start = args.offset
    end = (
        start + args.limit
        if args.limit is not None
        else None
    )

    df = all_news_df.iloc[start:end]

    enriched_news = []
    counts = Counter()

    print("\nENRIQUECIMIENTO SILVER")
    print(f"Origen: s3://{BUCKET}/{source_key}")
    print(f"Noticias disponibles: {total_news}")
    print(f"Noticias seleccionadas: {len(df)}")
    print(f"Offset: {args.offset}")
    print(f"Llamadas API autorizadas: {args.allow_api_calls}")

    if df.empty:
        print("\nNo hay noticias en el lote seleccionado.")
        return

    # 3. Enriquecer noticias
    for _, news in df.iterrows():
        result = enrich_news(
            title=news["title"],
            description=news["description"],
            allow_api_calls=args.allow_api_calls,
            use_s3_cache=True,
        )

        counts[result["status"]] += 1

        if result.get("cache_hit", False):
            counts["cache_hits"] += 1

        enriched_news.append({
            "news_id": news["news_id"],
            "content_hash": news["content_hash"],
            "enrichment": result,
        })

    # 4. Mostrar resumen
    print("\nRESUMEN")
    print(f"Procesados: {counts['processed']}")
    print(f"Pendientes: {counts['not_processed']}")
    print(f"Resultados reutilizados: {counts['cache_hits']}")

    # 5. Proteger publicación definitiva
    if not can_publish(
        total_news=total_news,
        selected_news=len(df),
        pending_news=counts["not_processed"],
    ):
        print(
            "\nPublicación bloqueada: ejecución parcial "
            "o noticias pendientes de enriquecimiento."
        )
        print("Los resultados procesados quedan en caché.")
        print("No se sobrescribirán las tablas Silver.")
        return

    # 6. Construir tablas
    entities_df, phrases_df = build_enrichment_tables(
        enriched_news
    )

    # 7. Crear identificador único
    now = datetime.now(timezone.utc)
    publication_id = uuid4().hex

    partition = (
        f"year={now:%Y}/"
        f"month={now:%m}/"
        f"day={now:%d}/"
        f"run_id={publication_id}"
    )

    entities_key = (
        f"silver/news_entities/{partition}/"
        f"news_entities.parquet"
    )

    phrases_key = (
        f"silver/news_key_phrases/{partition}/"
        f"news_key_phrases.parquet"
    )

    manifest_key = (
        f"silver/publications/{partition}/"
        f"manifest.json"
    )

    # 8. Guardar primero ambos archivos Parquet
    save_parquet(entities_df, entities_key)
    save_parquet(phrases_df, phrases_key)

    # 9. Crear manifiesto de publicación completa
    manifest = {
        "publication_id": publication_id,
        "status": "completed",
        "created_at_utc": now.isoformat(),
        "source_news": f"s3://{BUCKET}/{source_key}",
        "news_count": total_news,
        "entities_count": len(entities_df),
        "key_phrases_count": len(phrases_df),
        "entities_path": f"s3://{BUCKET}/{entities_key}",
        "key_phrases_path": f"s3://{BUCKET}/{phrases_key}",
    }

    # El manifiesto solo se escribe si ambos Parquet
    # se guardaron sin errores.
    save_json(manifest, manifest_key)

    print("\nPUBLICACIÓN COMPLETADA")
    print(f"Run ID: {publication_id}")
    print(f"Noticias: {total_news}")
    print(f"Entidades: {len(entities_df)}")
    print(f"Frases clave: {len(phrases_df)}")
    print(f"Manifest: s3://{BUCKET}/{manifest_key}")

    print("\nEnriquecimiento Silver finalizado correctamente.")


if __name__ == "__main__":
    main()
