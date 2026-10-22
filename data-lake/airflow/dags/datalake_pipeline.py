from datetime import datetime, timedelta
from pathlib import Path
import subprocess

from airflow import DAG
from airflow.operators.python import PythonOperator


PROJECT_ROOT = Path(
    "/opt/airflow/project"
)

DATA_LAKE = PROJECT_ROOT / "data-lake"


def run_script(script_path, arguments=None):
    command = [
        "python",
        str(DATA_LAKE / script_path),
    ]

    if arguments:
        command.extend(arguments)

    subprocess.run(
        command,
        cwd=str(PROJECT_ROOT),
        check=True,
    )


with DAG(
    dag_id="taller4_datalake_pipeline",
    description="Pipeline Bronze Silver Gold - El Tiempo",
    start_date=datetime(2026, 10, 22),
    schedule=None,
    catchup=False,
    max_active_runs=1,
    default_args={
        "owner": "datalake",
        "retries": 1,
        "retry_delay": timedelta(minutes=5),
    },
    tags=["taller4", "datalake"],
) as dag:

    bronze = PythonOperator(
        task_id="bronze_ingestion",
        python_callable=run_script,
        op_kwargs={
            "script_path": "src/ingestion/bronze_ingestion.py"
        },
    )

    silver = PythonOperator(
        task_id="silver_processing",
        python_callable=run_script,
        op_kwargs={
            "script_path": "src/processing/silver_processor.py"
        },
    )

    changes = PythonOperator(
        task_id="detect_changes",
        python_callable=run_script,
        op_kwargs={
            "script_path": "src/processing/news_change_detector.py"
        },
    )

    enrichment = PythonOperator(
        task_id="comprehend_enrichment",
        python_callable=run_script,
        op_kwargs={
            "script_path": "src/enrichment/enrichment_processor.py"
        },
    )

    gold = PythonOperator(
        task_id="gold_processing",
        python_callable=run_script,
        op_kwargs={
            "script_path": "src/processing/gold_processor.py"
        },
    )

    bronze >> silver >> changes >> enrichment >> gold
