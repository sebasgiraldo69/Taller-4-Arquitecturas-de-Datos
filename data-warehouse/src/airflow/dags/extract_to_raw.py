"""DAG: extract_to_raw

Extrae MySQL (RDS) y MongoDB (DocumentDB), sube los CSVs a la capa raw de S3
(particionados por batch_id = run_id de Airflow) y los carga en las tablas
raw.* de Redshift vía COPY.

s3://<bucket>/raw/mysql/<tabla>/batch_id=<run_id>/<tabla>.csv -> raw.mysql_<tabla>
s3://<bucket>/raw/mongo/<coleccion>/batch_id=<run_id>/<coleccion>.csv -> raw.mongo_<coleccion>

Cada corrida reemplaza por completo el contenido de las tablas raw con el
último extracto (ver redshift_load.py). El modelado (staging/intermediate/
quarantine/marts) corre después, en el DAG `transform_warehouse` (Task #9),
que ejecuta `dbt run` sobre estas tablas raw ya cargadas.
"""

import re
import tempfile
from datetime import timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.task_group import TaskGroup
from pendulum import datetime as pendulum_datetime

import extract_to_s3
import redshift_load


def _sanitize_run_id(run_id: str) -> str:
    """Convierte un run_id de Airflow (puede traer ':' y '+') en un batch_id seguro para usarlo como parte de una key de S3."""
    return re.sub(r"[^A-Za-z0-9_.-]", "_", run_id)


def _extract_mysql(**context):
    batch_id = _sanitize_run_id(context["run_id"])
    with tempfile.TemporaryDirectory() as tmp:
        return extract_to_s3.extract_and_upload_mysql(tmp, batch_id)


def _extract_mongo(**context):
    batch_id = _sanitize_run_id(context["run_id"])
    with tempfile.TemporaryDirectory() as tmp:
        return extract_to_s3.extract_and_upload_mongo(tmp, batch_id)


def _load_mysql_raw(**context):
    upload_results = context["ti"].xcom_pull(task_ids="mysql.extract_and_upload")
    return redshift_load.load_mysql_raw(upload_results)


def _load_mongo_raw(**context):
    upload_results = context["ti"].xcom_pull(task_ids="mongo.extract_and_upload")
    return redshift_load.load_mongo_raw(upload_results)


with DAG(
    dag_id="extract_to_raw",
    description="Extrae RDS MySQL y DocumentDB, sube CSVs a S3 y los carga en raw.* de Redshift",
    schedule=None,
    start_date=pendulum_datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 2, "retry_delay": timedelta(seconds=30)},
    tags=["taller4", "raw", "s3", "redshift"],
) as dag:

    with TaskGroup(group_id="mysql") as mysql_group:
        extract_mysql = PythonOperator(
            task_id="extract_and_upload",
            python_callable=_extract_mysql,
        )
        load_mysql = PythonOperator(
            task_id="load_to_redshift",
            python_callable=_load_mysql_raw,
        )
        extract_mysql >> load_mysql

    with TaskGroup(group_id="mongo") as mongo_group:
        extract_mongo = PythonOperator(
            task_id="extract_and_upload",
            python_callable=_extract_mongo,
        )
        load_mongo = PythonOperator(
            task_id="load_to_redshift",
            python_callable=_load_mongo_raw,
        )
        extract_mongo >> load_mongo

    # Cada grupo sube a un prefijo de S3 y escribe en tablas de Redshift
    # independientes (mysql_* vs. mongo_*), así que no comparten recurso y
    # pueden correr en paralelo -- a diferencia del proyecto original, que
    # serializaba sus cargas porque ambas escribían al mismo archivo DuckDB.
