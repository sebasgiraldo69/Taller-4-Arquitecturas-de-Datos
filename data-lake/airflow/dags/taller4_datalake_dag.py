from datetime import datetime, timedelta
import os
import subprocess

from airflow import DAG
from airflow.operators.python import PythonOperator

BASE_DIR = "/opt/airflow/data-lake"

DEFAULT_ARGS = {
    "owner": "taller4",
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
}


def ejecutar_script(ruta_script, argumentos=None):
    comando = [
        "python",
        os.path.join(BASE_DIR, ruta_script),
    ]

    if argumentos:
        comando.extend(argumentos)

    print("Ejecutando:", " ".join(comando))

    subprocess.run(
        comando,
        cwd=BASE_DIR,
        check=True,
        timeout=900,
    )


with DAG(
    dag_id="taller4_datalake_pipeline",
    description="Pipeline Bronze, Silver y Gold de noticias",
    default_args=DEFAULT_ARGS,
    start_date=datetime(2026, 10, 22),
    schedule=None,
    catchup=False,
    max_active_runs=1,
    tags=["taller4", "datalake"],
) as dag:

    bronze = PythonOperator(
        task_id="bronze_ingestion",
        python_callable=ejecutar_script,
        op_kwargs={
            "ruta_script": "src/ingestion/bronze_ingestion.py"
        },
    )

    validar_bronze = PythonOperator(
        task_id="bronze_validation",
        python_callable=ejecutar_script,
        op_kwargs={
            "ruta_script": "src/ingestion/bronze_validator.py"
        },
    )

    silver = PythonOperator(
        task_id="silver_processing",
        python_callable=ejecutar_script,
        op_kwargs={
            "ruta_script": "src/processing/silver_processor.py"
        },
    )

    cambios = PythonOperator(
        task_id="news_change_detection",
        python_callable=ejecutar_script,
        op_kwargs={
            "ruta_script": "src/processing/news_change_detector.py"
        },
    )

    enriquecimiento = PythonOperator(
        task_id="comprehend_enrichment",
        python_callable=ejecutar_script,
        op_kwargs={
            "ruta_script": "src/enrichment/enrichment_processor.py"
        },
    )

    gold = PythonOperator(
        task_id="gold_processing",
        python_callable=ejecutar_script,
        op_kwargs={
            "ruta_script": "src/processing/gold_processor.py"
        },
    )

    bronze >> validar_bronze >> silver >> cambios >> enriquecimiento >> gold
