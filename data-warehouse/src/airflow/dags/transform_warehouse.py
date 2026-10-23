"""DAG: transform_warehouse

Automatiza lo que corrimos a mano en el contenedor al validar el Task #8:
dbt deps -> seed -> intermediate -> quarantine -> snapshot -> marts -> test,
contra Redshift Serverless.

Se dispara manualmente después de `extract_to_raw` (que deja las tablas
raw_data.* cargadas). No comparten schedule a propósito -- correrlos por
separado es justo lo que necesitamos para las evidencias del Task #10
(carga inicial, lote incremental, cambio SCD2, fallo/reejecución, etc.),
donde conviene disparar cada DAG en el momento exacto que pide cada escenario.
"""

from datetime import timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from pendulum import datetime as pendulum_datetime

from dbt_runner import run_dbt

with DAG(
    dag_id="transform_warehouse",
    description="Construye snapshots y marts con dbt sobre Redshift, y valida con dbt test",
    schedule=None,
    start_date=pendulum_datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(seconds=30),
        "retry_exponential_backoff": True,
        "max_retry_delay": timedelta(minutes=5),
    },
    tags=["taller4", "dbt", "redshift"],
) as dag:
    packages = PythonOperator(task_id="dbt_deps", python_callable=run_dbt, op_args=["deps"])
    seed = PythonOperator(task_id="dbt_seed", python_callable=run_dbt, op_args=["seed"])
    intermediate = PythonOperator(
        task_id="dbt_run_intermediate",
        python_callable=run_dbt,
        op_args=["run", "path:models/intermediate"],
    )
    quarantine = PythonOperator(
        task_id="dbt_run_quarantine",
        python_callable=run_dbt,
        op_args=["run", "path:models/quarantine"],
    )
    snapshots = PythonOperator(task_id="dbt_snapshot", python_callable=run_dbt, op_args=["snapshot"])
    marts = PythonOperator(
        task_id="dbt_run_marts",
        python_callable=run_dbt,
        op_args=["run", "path:models/marts"],
    )
    tests = PythonOperator(task_id="dbt_test", python_callable=run_dbt, op_args=["test"])

    packages >> seed >> intermediate >> quarantine >> snapshots >> marts >> tests