"""Carga la capa raw de Redshift desde los CSVs subidos a S3, vía COPY.

Reutiliza MYSQL_CSV_COLUMNS/MONGO_CSV_COLUMNS de extract_to_s3.py como única
fuente de verdad del esquema (mismas columnas, mismos tipos, en el mismo
orden que los CSVs) para evitar que el DDL de Redshift se desalinee del CSV.

Cada ejecución del DAG reemplaza por completo el contenido de las tablas raw_data
(TRUNCATE + COPY) con el último batch extraído -- la capa raw siempre refleja
el estado de la fuente al momento de la última extracción, igual que hacía
el DuckDB del proyecto original (DELETE + INSERT completo en cada corrida).
"""

import os

import psycopg2

import extract_to_s3


def get_connection():
    return psycopg2.connect(
        host=os.environ["REDSHIFT_HOST"],
        port=int(os.getenv("REDSHIFT_PORT", "5439")),
        dbname=os.environ["REDSHIFT_DATABASE"],
        user=os.environ["REDSHIFT_USER"],
        password=os.environ["REDSHIFT_PASSWORD"],
    )


def _create_table_sql(schema, table, columns):
    column_defs = ",\n    ".join(f"{name} {dtype}" for name, dtype in columns.items())
    return f"CREATE TABLE IF NOT EXISTS {schema}.{table} (\n    {column_defs}\n)"


def ensure_raw_schema(conn):
    """Crea el esquema raw_data y las 6 tablas si no existen todavía (idempotente)."""
    with conn.cursor() as cur:
        cur.execute("CREATE SCHEMA IF NOT EXISTS raw_data")
        for table, columns in extract_to_s3.MYSQL_CSV_COLUMNS.items():
            cur.execute(_create_table_sql("raw_data", f"mysql_{table}", columns))
        for collection, columns in extract_to_s3.MONGO_CSV_COLUMNS.items():
            cur.execute(_create_table_sql("raw_data", f"mongo_{collection}", columns))
    conn.commit()


def copy_table(conn, schema, table, s3_uri, iam_role_arn, region):
    with conn.cursor() as cur:
        cur.execute(f"TRUNCATE TABLE {schema}.{table}")
        cur.execute(
            f"""
            COPY {schema}.{table}
            FROM %s
            IAM_ROLE %s
            CSV
            IGNOREHEADER 1
            TIMEFORMAT 'auto'
            DATEFORMAT 'auto'
            REGION %s
            """,
            (s3_uri, iam_role_arn, region),
        )
    conn.commit()


def _load(upload_results, name_prefix):
    iam_role_arn = os.environ["REDSHIFT_S3_ROLE_ARN"]
    region = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
    conn = get_connection()
    try:
        ensure_raw_schema(conn)
        loaded = {}
        for entity, info in upload_results.items():
            table = f"{name_prefix}_{entity}"
            copy_table(conn, "raw_data", table, info["s3_uri"], iam_role_arn, region)
            loaded[table] = info["rows"]
        return loaded
    finally:
        conn.close()


def load_mysql_raw(upload_results):
    """upload_results: lo que devuelve extract_to_s3.extract_and_upload_mysql (via XCom)."""
    return _load(upload_results, "mysql")


def load_mongo_raw(upload_results):
    """upload_results: lo que devuelve extract_to_s3.extract_and_upload_mongo (via XCom)."""
    return _load(upload_results, "mongo")