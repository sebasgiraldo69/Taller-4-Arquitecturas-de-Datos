{# Filtro de cargas incrementales para la fila candidata (alias candidate). Carga las llaves nuevas, las filas cuya fecha de negocio cae en la ventana de reproceso (desde incremental_lookback_days antes de la fecha máxima ya cargada) y las filas cuyas llaves de dimensión resueltas cambiaron (tracked_columns), por ejemplo cuando una versión SCD2 nueva reemplaza a la anterior.

Redshift no soporta el patrón de subquery correlacionado que usaba la
versión original (EXISTS correlacionado con varios IS DISTINCT FROM
combinados con OR -- falla con "This type of correlated subquery pattern
is not supported"). Se reescribió con LEFT JOIN, sin subqueries
correlacionadas, que es equivalente y sí corre en Redshift. #}
{% macro incremental_candidate_filter(key_column, business_date_column, tracked_columns=[]) %}
{% if is_incremental() %}
left join {{ this }} as existing on existing.{{ key_column }} = candidate.{{ key_column }}
left join (
    select max(dates.date) - {{ var('incremental_lookback_days') }} as cutoff_date
    from {{ this }} as existing_dates
    inner join {{ ref('dim_date') }} as dates on dates.date_sk = existing_dates.date_sk
) as lookback on true
where (
    existing.{{ key_column }} is null
    or candidate.{{ business_date_column }} >= lookback.cutoff_date
    {% if tracked_columns %}
    or (
        {% for column in tracked_columns %}
        existing.{{ column }} is distinct from candidate.{{ column }}{{ "" if loop.last else " or" }}
        {% endfor %}
    )
    {% endif %}
)
{% endif %}
{% endmacro %}

{# Elimina de la tabla de hechos las filas cuya llave de origen ya no existe en la capa validada. #}
{% macro delete_orphaned_facts(sk_column, source_relation, source_key) %}
delete from {{ this }}
where {{ sk_column }} not in (
    select {{ dbt_utils.generate_surrogate_key(['cast(' ~ source_key ~ ' as varchar)']) }}
    from {{ source_relation }}
)
{% endmacro %}