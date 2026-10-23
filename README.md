# Taller 4 — Arquitecturas de Datos

### Migración a AWS de un Data Warehouse y un Data Lake
*Proyecto académico — Ingeniería de Datos, Universidad EIA (2026-2)*

![AWS](https://img.shields.io/badge/AWS-us--east--1-FF9900?style=for-the-badge&logo=amazonwebservices&logoColor=white)
![Terraform](https://img.shields.io/badge/Terraform-IaC-7B42BC?style=for-the-badge&logo=terraform&logoColor=white)
![Airflow](https://img.shields.io/badge/Apache_Airflow-2.11.2-017CEE?style=for-the-badge&logo=apacheairflow&logoColor=white)
![dbt](https://img.shields.io/badge/dbt-1.9.4-FF694B?style=for-the-badge&logo=dbt&logoColor=white)
![Redshift](https://img.shields.io/badge/Redshift-Serverless-8C4FFF?style=for-the-badge&logo=amazonredshift&logoColor=white)
![DocumentDB](https://img.shields.io/badge/DocumentDB-MongoDB_API-47A248?style=for-the-badge&logo=mongodb&logoColor=white)
![QuickSight](https://img.shields.io/badge/QuickSight-Dashboards-FDB813?style=for-the-badge&logo=amazonwebservices&logoColor=white)
![Glue%20%26%20Athena](https://img.shields.io/badge/Glue_%26_Athena-Data_Catalog-232F3E?style=for-the-badge&logo=amazonwebservices&logoColor=white)
![Comprehend](https://img.shields.io/badge/Comprehend-NLP-01A88D?style=for-the-badge&logo=amazonwebservices&logoColor=white)

Este repositorio reúne dos retos del curso de Ingeniería de Datos de la Universidad EIA, ambos consistentes en migrar una solución que corría de forma local (con Docker Compose) hacia una arquitectura completamente en AWS, desplegada con Terraform y orquestada con Apache Airflow:

- **[`data-warehouse/`](./data-warehouse)** — migración de un flujo DuckDB + dbt (fuentes MySQL y MongoDB) hacia **Amazon RDS, DocumentDB, S3, Redshift Serverless y QuickSight**. Desarrollado por **Juan José Jaramillo Mora**.
- **[`data-lake/`](./data-lake)** — un data lake de arquitectura medallón (Bronze/Silver/Gold) que recopila noticias desde feeds RSS, las enriquece con **Amazon Comprehend** y las expone para consulta con **AWS Glue Data Catalog y Amazon Athena**. Desarrollado por **Sebastián Giraldo Franco**.

El enunciado completo de ambos retos está en [`Actividad Arquitecturas de Datos.pdf`](./Actividad%20Arquitecturas%20de%20Datos.pdf).

---

## Tabla de contenido

- [Alcance](#alcance)
- [Estructura del repositorio](#estructura-del-repositorio)
- [Parte 1 — Data Warehouse](#parte-1--data-warehouse)
- [Parte 2 — Data Lake](#parte-2--data-lake)
- [Modelo de seguridad común](#modelo-de-seguridad-común)
- [Tecnologías](#tecnologías)
- [Contexto académico](#contexto-académico)

---

## Alcance

| Reto | Servicio analítico | Orquestación | Visualización/consulta |
|---|---|---|---|
| Data Warehouse | Amazon Redshift Serverless (modelo estrella, dbt) | Apache Airflow + dbt en una EC2 | Amazon QuickSight |
| Data Lake | Amazon S3 (medallón Bronze/Silver/Gold) + AWS Glue Data Catalog | Apache Airflow en una EC2 | Amazon Athena |

Ambos retos comparten el mismo patrón de extremo a extremo: **extraer → aterrizar en S3 → transformar → servir**, cada uno con su propio motor analítico (Redshift para datos relacionales/documentales de un ecommerce; Athena/Glue para noticias no estructuradas enriquecidas con NLP).

---

## Estructura del repositorio

```
.
├── README.md                                 # Este archivo
├── Actividad Arquitecturas de Datos.pdf      # Enunciado de ambos retos
│
├── data-warehouse/
│   ├── terraform/            # S3, RDS MySQL, DocumentDB, Redshift Serverless, EC2, IAM, security groups
│   ├── docker/                # docker-compose.yml: Airflow + dbt en la EC2
│   ├── src/
│   │   ├── generate_data.py           # Datos sintéticos (clientes, productos, pedidos, reseñas, eventos)
│   │   ├── append_batch.py            # Lote diario reproducible (evidencia de carga incremental)
│   │   ├── simulate_changes.py        # Simula cambios de ciudad/categoría (evidencia de SCD2)
│   │   ├── extract_to_s3.py           # RDS MySQL + DocumentDB -> CSV -> S3 (capa raw)
│   │   ├── redshift_load.py           # S3 -> Redshift (COPY con rol IAM)
│   │   ├── dbt_runner.py              # Wrapper para ejecutar comandos dbt desde Airflow
│   │   ├── dbt/                       # Proyecto dbt completo (models, macros, snapshots, tests, seeds)
│   │   └── airflow/dags/
│   │       ├── extract_to_raw.py           # DAG: fuentes -> S3 -> raw_data.* en Redshift
│   │       └── transform_warehouse.py      # DAG: dbt deps/seed/run/snapshot/test orquestado
│   └── docs/
│       └── documentacion_final.md     # Arquitectura, decisiones, costos, seguridad, lecciones de Redshift
│
└── data-lake/
    ├── terraform/             # Bucket S3 único, Glue Data Catalog, Athena, EC2 para Airflow
    ├── config/
    │   └── rss_sources.yaml   # Feeds RSS seleccionados (El Tiempo: tecnología, cultura, deportes)
    ├── src/
    │   ├── ingestion/          # Extracción de RSS y validación de la capa Bronze
    │   ├── processing/         # Limpieza/normalización (Silver), detección de cambios, agregados (Gold)
    │   └── enrichment/         # Enriquecimiento de texto con Amazon Comprehend (con caché en S3)
    ├── cache/comprehend/       # Caché de resultados de Comprehend (evita reprocesar texto sin cambios)
    ├── tests/                  # Pruebas unitarias del pipeline
    └── airflow/
        ├── dags/taller4_datalake_dag.py   # DAG: bronze -> validación -> silver -> cambios -> enriquecimiento -> gold
        └── docker/                         # Dockerfile + docker-compose.yml de Airflow
```

---

## Parte 1 — Data Warehouse

**Objetivo del reto:** migrar el flujo local DuckDB + dbt (repositorio DE-DW del curso) a AWS, conservando las reglas de negocio del modelo dimensional y garantizando que el procesamiento sea reproducible, verificable y seguro.

### Arquitectura

```
┌─────────────┐   ┌──────────────┐
│  RDS MySQL  │   │  DocumentDB  │
│ (ecommerce) │   │ (reviews,    │
│             │   │  navigation) │
└──────┬──────┘   └──────┬───────┘
       └────────┬────────┘
                 │  extract_to_s3.py (Airflow)
                 ▼
        ┌─────────────────┐
        │   S3 (raw zone)  │  raw/<fuente>/<entidad>/batch_id=<id>/*.csv
        └────────┬────────┘
                 │  redshift_load.py — COPY ... IAM_ROLE
                 ▼
     ┌───────────────────────────┐
     │  Redshift Serverless      │
     │  raw_data → intermediate  │
     │  → quarantine → marts     │   ← dbt (dbt-redshift)
     └─────────────┬─────────────┘
                   ▼
          ┌──────────────────┐
          │  Amazon QuickSight │  Dashboard: gráfico + indicador
          └──────────────────┘

Orquestación: EC2 (t3.medium) — Airflow 2.11.2 + dbt 1.9.4, vía Docker Compose
  DAG extract_to_raw:       RDS/DocumentDB -> S3 -> raw_data.* en Redshift
  DAG transform_warehouse:  dbt deps -> seed -> intermediate -> quarantine -> snapshot -> marts -> test
```

### Qué se implementó

- **Fuentes migradas:** MySQL local → RDS MySQL (`db.t3.micro`); MongoDB local → Amazon DocumentDB (`db.t3.medium`).
- **Extracción incremental a S3:** cada corrida particiona por `fuente/entidad/batch_id`, conservando los CSV originales para poder reprocesar un lote sin volver a consultar las fuentes.
- **Carga a Redshift:** `COPY` desde S3 autorizado por un rol IAM dedicado (sin credenciales estáticas), esquema `raw_data` (renombrado de `raw`, palabra reservada en Redshift).
- **Modelo dimensional completo en dbt:** capas `intermediate` (staging + calidad), `quarantine` (rechazados con motivo), `marts` (dimensiones SCD tipo 2 + hechos incrementales), adaptado de DuckDB a Redshift (ver las [lecciones de dialecto](./data-warehouse/docs/documentacion_final.md#5-lecciones-técnicas-redshift-vs-duckdb)).
- **Orquestación con Airflow:** dos DAGs independientes (`extract_to_raw` y `transform_warehouse`) ejecutados en la misma EC2 donde corre dbt, con reintentos acotados y logs por tarea/lote.
- **Evidencias de calidad e incrementalidad:** los 6 escenarios requeridos (carga inicial, registros defectuosos, repetición de lote, carga incremental, cambio SCD2, fallo/reejecución) reproducidos y verificados contra AWS.
- **Dashboard en QuickSight:** conectado directamente a `marts.fct_sales` (vía SQL personalizado que une las dimensiones), con gráfico de ventas por categoría, tabla por mes/canal e indicador de ventas totales, validado contra una consulta SQL directa a Redshift.

**Documentación completa** (arquitectura, decisiones técnicas, estimación de costos, controles de seguridad y las 7 lecciones de dialecto Redshift vs. DuckDB): [`data-warehouse/docs/documentacion_final.md`](./data-warehouse/docs/documentacion_final.md).

**Reproducción:** instrucciones de despliegue (Terraform), ejecución (Docker Compose + Airflow UI) y eliminación de recursos en la misma documentación.

---

## Parte 2 — Data Lake

**Objetivo del reto:** construir un data lake de arquitectura medallón en Amazon S3 que recopile noticias desde feeds RSS, las limpie y enriquezca con procesamiento de lenguaje natural, y las exponga para consulta SQL vía AWS Glue Data Catalog y Amazon Athena.

### Arquitectura

```
┌─────────────┐   ┌──────────────────────────┐
│ Fuentes RSS │   │  EC2 · Airflow + tareas   │
│ (El Tiempo) │   │  Python                   │
└──────┬──────┘   └────┬──────────────────┬───┘
       │ Extracción     │ Invoca           │ Orquesta
       ▼                ▼                  │
┌─────────────┐  ┌──────────────┐          │
│ S3 · Bronze │  │   Amazon     │          │
│ (originales)│  │  Comprehend  │          │
└──────┬──────┘  │ (entidades,  │          │
       │Limpieza │  frases clave)│         │
       │enriquec.│  └──────┬─────┘         │
       ▼                   │               │
┌─────────────┐            │               │
│ S3 · Silver │◄───────────┘               │
│ (normalizado)│                           │
└──────┬──────┘                            │
       │ Agregaciones                      │
       ▼                                   │
┌─────────────┐    ┌───────────────────┐   │
│  S3 · Gold   │◄──┤ AWS Glue Data      │◄──┘
│ (indicadores)│   │ Catalog (metadatos)│
└──────┬──────┘    └────────┬──────────┘
       └──────────► Amazon Athena (consultas SQL) ◄┘
```

### Qué se implementó

- **Fuentes RSS:** tres secciones del feed de El Tiempo — tecnología, cultura y deportes (`data-lake/config/rss_sources.yaml`).
- **Capa Bronze:** ingesta Python (`src/ingestion/bronze_ingestion.py`) que conserva la respuesta original de cada feed en S3, registrando fuente, URL, fecha/hora UTC, estado HTTP y hash del contenido; `bronze_validator.py` valida cada lote.
- **Capa Silver:** limpieza, normalización de fechas a UTC, deduplicación y detección de cambios en noticias ya procesadas (`src/processing/silver_processor.py`, `news_change_detector.py`), separando los registros inválidos en una ruta de cuarentena con su motivo.
- **Enriquecimiento con Amazon Comprehend:** extracción de personas, organizaciones, lugares y frases clave sobre título y descripción, con caché en S3 (`data-lake/cache/comprehend/`) para evitar reprocesar texto sin cambios (`src/enrichment/`).
- **Capa Gold:** agregados analíticos (`src/processing/gold_processor.py`) — noticias por día/medio/sección, entidades y frases clave más frecuentes, cambios de presencia de una entidad entre fechas.
- **Catálogo y consulta:** tablas de Silver y Gold registradas en AWS Glue Data Catalog; consultas SQL sobre S3 vía Amazon Athena, con formato Parquet y particionamiento por fecha.
- **Orquestación con Airflow:** un único DAG (`taller4_datalake_pipeline`) que encadena `bronze_ingestion → bronze_validation → silver_processing → news_change_detection → comprehend_enrichment → gold_processing`, desplegado en una EC2 vía Docker Compose.
- **Pruebas unitarias:** cobertura sobre el enriquecimiento con Comprehend, la detección de cambios, la publicación de resultados y la caché en S3 (`data-lake/tests/`).

---

## Modelo de seguridad común

Ambos retos siguen los mismos principios de seguridad, consistentes con el enfoque de mínimo privilegio del curso:

| Principio | Cómo se aplicó |
|---|---|
| Sin credenciales estáticas de AWS | Toda interacción con S3, Redshift y Comprehend usa **roles IAM** (instance profile de la EC2, rol propio de Redshift para `COPY`), nunca access keys embebidas en el código |
| Buckets S3 privados | Acceso público bloqueado explícitamente (`block_public_acls`, `block_public_policy`, etc.), cifrado en reposo (SSE-AES256) y versionado habilitado |
| Red restringida | Los security groups de RDS, DocumentDB, Redshift y las instancias EC2 solo admiten las IPs/orígenes estrictamente necesarios (IP de administración resuelta dinámicamente, SG de la propia EC2, rango publicado por AWS para QuickSight) — nunca `0.0.0.0/0` salvo en egress |
| Infraestructura como código | Todo el despliegue (ambos retos) se hace con Terraform, versionado en este repositorio, sin recursos creados manualmente desde la consola |
| Llaves y estado fuera del control de versiones | `.gitignore` excluye `*.tfstate`, `.terraform/`, `*.pem`, `*.key` y cualquier archivo de credenciales |

---

## Tecnologías

| Categoría | Herramientas |
|---|---|
| Nube | AWS (us-east-1): IAM, VPC, EC2, S3, RDS (MySQL), DocumentDB, Redshift Serverless, QuickSight, Glue Data Catalog, Athena, Comprehend |
| Infraestructura | Terraform |
| Orquestación | Apache Airflow 2.11.2 (Docker Compose, por reto) |
| Transformación | dbt 1.9.4 + dbt-redshift 1.9.1 (data warehouse); scripts Python de procesamiento por capas (data lake) |
| Lenguajes | Python, SQL (dbt/Redshift y Athena), HCL |
| Librerías clave | `boto3`, `pymysql`, `pymongo`, `psycopg2` |
| Entorno de desarrollo | Windows 11, WSL2 (Ubuntu), VS Code |

---

## Contexto académico

Actividad del curso **Ingeniería de Datos** de la **Universidad EIA**, periodo **2026-2**, bajo la consigna "Arquitecturas de Datos": migrar dos soluciones que corrían localmente hacia arquitecturas completamente administradas en AWS, evaluando extracción desde fuentes relacionales y documentales, orquestación con Airflow, transformación reproducible y verificable, controles de seguridad y presentación de resultados mediante visualización/consulta SQL.

**Autores**

- Juan José Jaramillo Mora — [@Juanjo1414](https://github.com/Juanjo1414) — Data Warehouse
- Sebastián Giraldo Franco — [@sebasgiraldo69](https://github.com/sebasgiraldo69) — Data Lake