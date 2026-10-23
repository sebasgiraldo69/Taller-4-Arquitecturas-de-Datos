"""Ejecuta comandos de dbt desde tareas reutilizables de Airflow.

Adaptación de ecommerce_dw/transformations/dbt_runner.py del proyecto
original: la misma idea (subprocess.run envolviendo el binario de dbt), pero
sin el fcntl.flock que ahí serializaba el acceso al archivo DuckDB (single
writer). Redshift es una base de verdad con control de concurrencia propio,
así que ese lock no hace falta.
"""

import logging
import subprocess
from pathlib import Path

DBT_EXECUTABLE = "/home/airflow/dbt-venv/bin/dbt"
DBT_PROJECT = Path("/opt/airflow/src/dbt")
LOGGER = logging.getLogger(__name__)


def run_dbt(command, selector=None):
    arguments = [
        DBT_EXECUTABLE,
        command,
        "--project-dir", str(DBT_PROJECT),
        "--profiles-dir", str(DBT_PROJECT),
    ]
    if selector is not None:
        arguments.extend(["--select", selector])

    LOGGER.info("Running dbt command: %s", " ".join(arguments))
    subprocess.run(arguments, check=True)