"""Extrae MySQL/MongoDB a CSV y los sube a S3 (capa raw), particionados por batch_id.

Adaptación de ecommerce_dw/ingestion/raw_ingestion.py del proyecto original: la
lógica de extracción (conexión, armado de CSVs) es la misma; lo que cambia es
el destino — en vez de cargar a un DuckDB local, sube los CSVs a
s3://<bucket>/raw/<fuente>/<entidad>/batch_id=<batch_id>/<entidad>.csv
"""

import csv
import os
from datetime import datetime
from pathlib import Path

import boto3
import pymysql
from bson import json_util
from pymongo import MongoClient
from pymysql.cursors import SSCursor

BATCH_SIZE = 1000

# _loaded_at/_source son columnas de linaje: cuándo se extrajo la fila y de
# qué fuente vino. Los modelos stg_*.sql del proyecto original las esperan
# en las tablas raw (select ..., _loaded_at, _source from {{ source(...) }}).
_LINEAGE_COLUMNS = {"_loaded_at": "TIMESTAMP", "_source": "VARCHAR(50)"}

# IMPORTANTE: en Redshift "VARCHAR" sin tamaño equivale a VARCHAR(256), y el
# COPY falla en silencio (solo deja "Load into table '<tabla>' failed" sin
# más detalle) cuando un valor no entra en esa longitud -- especial cuidado
# con document_json, que lleva el documento Mongo completo serializado.
MYSQL_CSV_COLUMNS = {
    "customers": {"customer_id": "BIGINT", "name": "VARCHAR(255)", "email": "VARCHAR(255)", "phone": "VARCHAR(50)", "city": "VARCHAR(100)", "department": "VARCHAR(100)", "registration_date": "DATE", "updated_at": "TIMESTAMP", **_LINEAGE_COLUMNS},
    "products": {"product_id": "BIGINT", "name": "VARCHAR(255)", "category": "VARCHAR(100)", "price": "DECIMAL(12,2)", "description": "VARCHAR(2000)", "is_active": "BOOLEAN", "updated_at": "TIMESTAMP", **_LINEAGE_COLUMNS},
    "orders": {"order_id": "BIGINT", "customer_id": "BIGINT", "order_date": "TIMESTAMP", "status": "VARCHAR(50)", "sales_channel": "VARCHAR(50)", "payment_method": "VARCHAR(50)", "total": "DECIMAL(14,2)", **_LINEAGE_COLUMNS},
    "order_items": {"order_item_id": "BIGINT", "order_id": "BIGINT", "product_id": "BIGINT", "quantity": "INTEGER", "unit_price": "DECIMAL(12,2)", "subtotal": "DECIMAL(14,2)", **_LINEAGE_COLUMNS},
}
MONGO_CSV_COLUMNS = {
    "reviews": {"review_id": "BIGINT", "customer_id": "BIGINT", "product_id": "BIGINT", "rating": "INTEGER", "reviewed_at": "TIMESTAMPTZ", "document_json": "VARCHAR(65535)", **_LINEAGE_COLUMNS},
    "navigation_events": {"event_id": "BIGINT", "event_type": "VARCHAR(50)", "occurred_at": "TIMESTAMPTZ", "customer_id": "BIGINT", "product_id": "BIGINT", "sales_channel": "VARCHAR(50)", "document_json": "VARCHAR(65535)", **_LINEAGE_COLUMNS},
}


def connect_mysql():
    return pymysql.connect(
        host=os.environ["MYSQL_HOST"],
        port=int(os.getenv("MYSQL_PORT", "3306")),
        user=os.environ["MYSQL_USER"],
        password=os.environ["MYSQL_PASSWORD"],
        database=os.getenv("MYSQL_DATABASE", "ecommerce"),
        charset="utf8mb4",
        cursorclass=SSCursor,
    )


def flatten_mongo_review(document, loaded_at):
    customer = document.get("customer") or {}
    product = document.get("product") or {}
    return (
        document.get("review_id"), customer.get("customer_id"), product.get("product_id"),
        document.get("rating"), document.get("reviewed_at"), json_util.dumps(document),
        loaded_at, "documentdb",
    )


def flatten_mongo_event(document, loaded_at):
    customer = document.get("customer") or {}
    product = document.get("product") or {}
    device = document.get("device") or {}
    return (
        document.get("event_id"), document.get("event_type"), document.get("occurred_at"),
        customer.get("customer_id"), product.get("product_id"), device.get("sales_channel"),
        json_util.dumps(document), loaded_at, "documentdb",
    )


def _csv_value(value):
    if isinstance(value, datetime):
        return value.isoformat(sep=" ")
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def _write_csv(path, headers, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(headers)
        count = 0
        for row in rows:
            writer.writerow([_csv_value(value) for value in row])
            count += 1
    temporary.replace(path)
    return count


def extract_mysql(directory):
    """Extrae las 4 tablas de RDS MySQL a CSV local. No toca S3 todavía."""
    loaded_at = datetime.utcnow()
    source = connect_mysql()
    outputs = {}
    try:
        for table, columns in MYSQL_CSV_COLUMNS.items():
            cursor = source.cursor()
            try:
                business_columns = [c for c in columns if c not in _LINEAGE_COLUMNS]
                cursor.execute(f"SELECT * FROM {table} ORDER BY {business_columns[0]}")
                path = Path(directory) / f"mysql_{table}.csv"

                def rows():
                    while batch := cursor.fetchmany(BATCH_SIZE):
                        for row in batch:
                            yield (*row, loaded_at, "rds_mysql")

                outputs[table] = {"path": str(path), "rows": _write_csv(path, columns, rows())}
            finally:
                cursor.close()
    finally:
        source.close()
    return outputs


def extract_mongo(directory):
    """Extrae las 2 colecciones de DocumentDB a CSV local (vía TLS). No toca S3 todavía."""
    loaded_at = datetime.utcnow()
    client = MongoClient(os.environ["MONGODB_URI"], tz_aware=True)
    outputs = {}
    try:
        database = client[os.getenv("MONGO_DATABASE", "ecommerce")]
        flatteners = {"reviews": flatten_mongo_review, "navigation_events": flatten_mongo_event}
        for collection, columns in MONGO_CSV_COLUMNS.items():
            cursor = database[collection].find({}).sort("_id", 1).batch_size(BATCH_SIZE)
            flatten = flatteners[collection]

            def rows():
                for document in cursor:
                    yield flatten(document, loaded_at)

            path = Path(directory) / f"mongo_{collection}.csv"
            outputs[collection] = {"path": str(path), "rows": _write_csv(path, columns, rows())}
    finally:
        client.close()
    return outputs


def upload_to_s3(local_path, source, entity, batch_id):
    """Sube un CSV local a s3://<bucket>/raw/<source>/<entity>/batch_id=<batch_id>/<entity>.csv

    Las credenciales las resuelve boto3 automáticamente desde el rol IAM
    asociado a la instancia EC2 (instance profile) — no hace falta access key.
    """
    bucket = os.environ["S3_BUCKET"]
    key = f"raw/{source}/{entity}/batch_id={batch_id}/{entity}.csv"
    s3 = boto3.client("s3", region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"))
    s3.upload_file(str(local_path), bucket, key)
    return f"s3://{bucket}/{key}"


def extract_and_upload_mysql(directory, batch_id):
    """Extrae MySQL a CSV local y sube cada archivo a S3. Devuelve conteos y rutas S3."""
    extracts = extract_mysql(directory)
    results = {}
    for table, info in extracts.items():
        s3_uri = upload_to_s3(info["path"], "mysql", table, batch_id)
        results[table] = {"s3_uri": s3_uri, "rows": info["rows"]}
    return results


def extract_and_upload_mongo(directory, batch_id):
    """Extrae DocumentDB a CSV local y sube cada archivo a S3. Devuelve conteos y rutas S3."""
    extracts = extract_mongo(directory)
    results = {}
    for collection, info in extracts.items():
        s3_uri = upload_to_s3(info["path"], "mongo", collection, batch_id)
        results[collection] = {"s3_uri": s3_uri, "rows": info["rows"]}
    return results


if __name__ == "__main__":
    import sys
    import tempfile

    batch = sys.argv[1] if len(sys.argv) > 1 else datetime.utcnow().strftime("manual_%Y%m%d_%H%M%S")
    with tempfile.TemporaryDirectory() as tmp:
        mysql_results = extract_and_upload_mysql(tmp, batch)
        mongo_results = extract_and_upload_mongo(tmp, batch)
        print(f"batch_id={batch}")
        for table, info in {**mysql_results, **mongo_results}.items():
            print(f"  {table}: {info['rows']} filas -> {info['s3_uri']}")