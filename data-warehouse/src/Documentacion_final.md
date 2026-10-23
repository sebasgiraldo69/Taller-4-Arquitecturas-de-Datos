# Taller 4 — Arquitecturas de Datos: Data Warehouse en AWS

**Alcance de este documento:** la parte de **data warehouse** del taller (migración de un flujo local MySQL/MongoDB → DuckDB/dbt hacia AWS). La parte de data lake la desarrolla el compañero de equipo en una carpeta separada del mismo repositorio.

---

## 1. Resumen ejecutivo

Se migró un data warehouse analítico (modelo estrella con dimensiones SCD tipo 2, hechos incrementales, capa de calidad/cuarentena, construido con dbt) desde un entorno local basado en Docker Compose + DuckDB hacia una arquitectura completamente administrada en AWS, usando **únicamente Terraform** para el despliegue de infraestructura y automatizando el pipeline de transformación con **Apache Airflow**.

Todo el código, la infraestructura como código y las evidencias de los escenarios de calidad/incrementalidad quedaron versionados en el repositorio del taller, carpeta `data-warehouse/`.

---

## 2. Arquitectura

### 2.1 Diagrama lógico

```
┌─────────────┐   ┌──────────────┐
│  RDS MySQL  │   │  DocumentDB  │        Fuentes transaccionales
│ (ecommerce) │   │ (reviews,    │        (equivalentes a las fuentes
│             │   │  navigation) │         locales MySQL/MongoDB)
└──────┬──────┘   └──────┬───────┘
       │                 │
       └────────┬────────┘
                 │  extract_to_s3.py (Airflow, PythonOperator)
                 ▼
        ┌─────────────────┐
        │   S3 (raw zone)  │   s3://.../raw/<fuente>/<entidad>/batch_id=<run_id>/*.csv
        └────────┬────────┘
                 │  redshift_load.py — COPY ... IAM_ROLE (sin credenciales estáticas)
                 ▼
     ┌───────────────────────────┐
     │  Redshift Serverless      │
     │  raw_data.* (staging)     │
     │  intermediate.* (stg/qa)  │
     │  quarantine.* (rechazados)│
     │  marts.* (modelo estrella)│   ← dbt (dbt-redshift)
     └─────────────┬─────────────┘
                   │
                   ▼
          ┌──────────────────┐
          │   Amazon QuickSight│   Dashboard: gráfico + indicador (+ filtro)
          └──────────────────┘

Orquestación: EC2 (t3.medium) — Airflow 2.11.2 + dbt 1.9.4 (dbt-redshift 1.9.1), vía Docker Compose
  DAG extract_to_raw:       RDS/DocumentDB -> S3 -> raw_data.* en Redshift
  DAG transform_warehouse:  dbt deps -> seed -> intermediate -> quarantine -> snapshot -> marts -> test
```

### 2.2 Mapeo de componentes (local → AWS)

| Componente local (DE-DW) | Componente AWS | Notas |
| --- | --- | --- |
| MySQL (Docker) | **RDS MySQL** (db.t3.micro) | Mismo esquema (`customers`, `products`, `orders`, `order_items`) |
| MongoDB (Docker) | **Amazon DocumentDB** (db.t3.medium) | Colecciones `reviews`, `navigation_events` |
| DuckDB (archivo local) | **Amazon Redshift Serverless** | Base `ecommerce_dw`, namespace/workgroup dedicados, 8 RPU base |
| Filesystem local (capa raw) | **Amazon S3** | Bucket `taller4-datawarehouse-juanjo1414`, capa `raw/` particionada por fuente/entidad/batch_id |
| Airflow + dbt (Docker Compose local) | **EC2 (t3.medium)** con Docker Compose | Mismo stack de contenedores, desplegado en la nube |
| — | **Amazon QuickSight** | No existe equivalente local; es la capa de visualización nueva |

### 2.3 Por qué estas decisiones

- **Redshift Serverless en vez de clúster provisionado**: cobra solo por uso (RPU-hora), ideal para una carga de trabajo intermitente como un taller académico. Un clúster provisionado cobraría 24/7 aunque no se use.
- **VPC default** (no VPC dedicada): reduce la complejidad de red (NAT gateways, tablas de rutas) sin sacrificar seguridad, ya que el control de acceso real lo dan los security groups, no el aislamiento de VPC.
- **IP dinámica en Terraform** (`data "http" "my_ip"`): como se trabaja desde una red doméstica con IP cambiante, cada `terraform apply` resuelve automáticamente la IP pública actual y actualiza las reglas de los security groups — evita tener que editar `terraform.tfvars` a mano cada vez que cambia la IP.
- **EC2 única para Airflow+dbt** (en vez de servicios administrados como MWAA): minimiza el costo manteniendo el mismo stack de contenedores que el proyecto local, con el tradeoff de que el mantenimiento (parches, reinicios) corre por cuenta del estudiante.

---

## 3. Seguridad

| Control | Detalle |
| --- | --- |
| **Sin credenciales estáticas de AWS en el código** | Tanto la extracción (`extract_to_s3.py`) como la carga a Redshift (`redshift_load.py`) usan **roles IAM** adjuntos por instance profile (EC2) o por rol propio de Redshift (`COPY ... IAM_ROLE`), nunca access keys embebidas |
| **Rol IAM de mínimo privilegio para S3** | `taller4-dw-ec2-s3-access` (EC2, lectura/escritura) y `taller4-dw-redshift-s3-access` (Redshift, solo lectura) son roles separados, cada uno con el permiso mínimo necesario para su función |
| **Acceso a RDS/DocumentDB restringido por IP** | Security groups permiten conexión al puerto de MySQL/DocumentDB únicamente desde la IP pública actual de administración (resuelta dinámicamente) y desde la EC2 de Airflow — nunca abierto a `0.0.0.0/0` |
| **Acceso a Redshift restringido** | Igual que arriba, más una regla adicional explícita para el rango de IPs publicado por AWS para QuickSight (`52.23.63.224/27` en us-east-1) — acceso de solo ese servicio, no abierto al público |
| **Usuarios IAM separados por función** | La cuenta tiene un usuario sin permisos (`Prueba_Ingenieria_De_Datos`, para pruebas de restricción) y un usuario administrador (`juan_admin`) usado exclusivamente para Terraform/consola |
| **Llave SSH fuera del control de versiones** | `ec2_key` está en `.gitignore`; nunca se subió al repositorio |

---

## 4. Costos (orden de magnitud, minimizando gasto)

| Recurso | Tamaño elegido | Justificación de costo |
| --- | --- | --- |
| RDS MySQL | db.t3.micro | El tamaño mínimo que soporta el motor; volumen de datos del taller es pequeño |
| DocumentDB | db.t3.medium | Tamaño mínimo soportado por DocumentDB (no ofrece instancias más chicas) |
| EC2 (Airflow+dbt) | t3.medium | Se subió desde t3.small porque 2GB de RAM no alcanzaban para construir la imagen Docker con dbt-core+dbt-redshift; se mantiene en t3.medium de forma permanente |
| Redshift | **Serverless**, 8 RPU base | Cobra por RPU-segundo solo cuando hay consultas activas, a diferencia de un clúster provisionado que cobra 24/7 |
| S3 | Est. estándar | Volumen de datos del taller es de unos pocos MB, costo despreciable |
| QuickSight | Edición **Standard**, trial de 30 días | La edición más barata ($9/usuario/mes fuera del trial); no se usó Enterprise |

---

## 5. Lecciones técnicas: Redshift vs. DuckDB

Migrar el proyecto dbt de DuckDB a Redshift expuso varias incompatibilidades de dialecto SQL que no son evidentes a priori. Quedan documentadas aquí porque son el tipo de detalle que un dictamen de arquitectura necesita justificar:

1. **`raw` es palabra reservada en Redshift.** El esquema de staging se tuvo que renombrar de `raw` a `raw_data` en todo el proyecto (`CREATE SCHEMA IF NOT EXISTS raw` fallaba con error de sintaxis).
2. **`VARCHAR` sin longitud explícita = `VARCHAR(256)` en Redshift**, a diferencia de DuckDB donde es ilimitado por defecto. Esto rompía silenciosamente el `COPY` de la columna `document_json` (el documento completo de MongoDB serializado, que supera los 256 caracteres). Se corrigió dando tamaño explícito a cada columna `VARCHAR`.
3. **`extract(isodow from date)` no existe en Redshift** (es específico de DuckDB/Postgres moderno). Redshift solo tiene `extract(dow from date)` (0=domingo..6=sábado). Se convirtió manualmente a numeración ISO (1=lunes..7=domingo) con un `CASE`.
4. **Sintaxis JSONPath distinta.** `json_extract_string(doc, '$.a.b')` (DuckDB) no existe en Redshift; el equivalente es `json_extract_path_text(doc, 'a', 'b')`, con un argumento de texto por nivel de anidamiento.
5. **`CAST(varchar AS boolean)` no soportado directamente en Redshift** (sí en DuckDB/Postgres). Se reemplazó por un `CASE` explícito (`CASE lower(expr) WHEN 'true' THEN true WHEN 'false' THEN false ELSE null END`).
6. **Límite en subqueries correlacionadas.** El planificador de consultas de Redshift rechaza ciertos patrones de `EXISTS` correlacionado combinados con múltiples `IS DISTINCT FROM` ("This type of correlated subquery pattern is not supported due to internal error"). Se reescribió el macro de filtro incremental usando `LEFT JOIN` en vez de `EXISTS` correlacionado — funcionalmente equivalente, pero compatible.
7. **`incremental_strategy='delete+insert'` en dbt-redshift 1.9.1 genera SQL inválido para Redshift.** El macro genera `DELETE FROM tabla AS alias WHERE ...`, y la sintaxis `DELETE FROM ... AS alias` no es válida en Redshift (sí en Postgres, de donde parece estar adaptado el macro). Se cambió la estrategia incremental a `'merge'`, que Redshift sí soporta de forma nativa vía `MERGE INTO`.

**Lección general:** los bugs de los puntos 6 y 7 solo se manifestaron en la **segunda** corrida de los modelos incrementales — la primera corrida construye la tabla desde cero con un `CREATE TABLE AS` simple, sin pasar por la rama `is_incremental()` donde vive la lógica problemática. Por eso, al validar un modelo incremental migrado de dialecto, siempre hay que probar una segunda corrida contra una tabla que ya existe, no solo la primera.

---

## 6. Evidencias de calidad e incrementalidad (Task #10)

Los 6 escenarios requeridos se reprodujeron contra el ambiente de AWS y quedaron verificados:

| # | Escenario | Resultado verificado |
| --- | --- | --- |
| 1 | Carga inicial | DAGs `extract_to_raw` + `transform_warehouse` corridos de punta a punta, status `success` |
| 2 | Registros defectuosos | 32 filas en 6 tablas de `quarantine.*`, 2 de cada uno de 16 motivos de rechazo distintos |
| 3 | Repetición de lote (idempotencia) | Pipeline completo corrido 2 veces sin tocar fuentes; huella de `fct_sales` idéntica antes/después (253 filas / 253 llaves / $7,293,790.26) |
| 4 | Carga incremental | Lote nuevo (`append_batch.py --batch-id 2`): +3 filas en cada hecho (253→256, 150→153, 500→503); repetir el lote no duplicó nada |
| 5 | Cambio SCD2 | `simulate_changes.py` cambió cliente 1 (Bogotá→Medellín) y producto 1 (Electrónica→Hogar); `dim_customer`/`dim_product` versionaron correctamente, 0 duplicados de `is_current`, point-in-time correcto en `fct_sales` |
| 6 | Fallo y reejecución | Documentado con fallos reales ocurridos durante el desarrollo: `dbt_snapshot`/`dbt_run_marts`/`dbt_test` fallaron en el intento 1 y el DAG completó en `success` gracias al retry automático de Airflow (`retries: 2`) |

---

## 7. Dashboard (QuickSight)

- **Fuente de datos:** conexión directa a Redshift Serverless vía red pública, con el security group ajustado para el rango de IPs de QuickSight.
- **Dataset:** consulta SQL personalizada que une `marts.fct_sales` con `dim_date`, `dim_product`, `dim_customer` y `dim_sales_channel` para exponer columnas legibles (categoría de producto, ciudad, canal, fecha) en vez de solo llaves subrogadas.
- **Elementos visuales incluidos:**
  - Gráfico de barras: ventas totales por categoría de producto
  - Tabla: subtotal por mes y canal de venta
  - Indicador (KPI): total de ventas (`SUM(subtotal)`)
- **Consulta de validación** (corrida en Redshift para confirmar que el KPI coincide con el warehouse):
  ```sql
  SELECT ROUND(SUM(subtotal), 2) AS total_ventas_validacion
  FROM marts.fct_sales;
  ```

---

## 8. Estructura del repositorio (`data-warehouse/`)

```
data-warehouse/
├── terraform/          # Infraestructura como código (S3, RDS, DocumentDB, Redshift, EC2, IAM, security groups)
├── docker/              # docker-compose.yml para Airflow + dbt en la EC2
├── src/
│   ├── generate_data.py       # Generador de datos sintéticos (clientes, productos, pedidos, reseñas, eventos)
│   ├── append_batch.py        # Agrega un lote diario reproducible (evidencia de carga incremental)
│   ├── simulate_changes.py    # Simula cambios de ciudad/categoría (evidencia de SCD2)
│   ├── extract_to_s3.py       # Extrae RDS MySQL + DocumentDB a CSV y sube a S3
│   ├── redshift_load.py       # Carga la capa raw_data.* en Redshift vía COPY
│   ├── dbt_runner.py          # Wrapper de subprocess para ejecutar comandos dbt desde Airflow
│   ├── dbt/                   # Proyecto dbt completo (models, macros, snapshots, tests, seeds)
│   └── airflow/dags/
│       ├── extract_to_raw.py       # DAG: fuentes -> S3 -> raw_data.*
│       └── transform_warehouse.py  # DAG: dbt deps -> seed -> intermediate -> quarantine -> snapshot -> marts -> test
└── docs/
    └── documentacion_final.md     # Este documento
```