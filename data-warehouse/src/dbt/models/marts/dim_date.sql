{% set start_date = var('date_dimension_start') %}
{% set end_date = var('date_dimension_end') %}

with date_spine as (
    select cast(date_day as date) as date
    from (
        {{ dbt_utils.date_spine(
        datepart='day',
        start_date="cast('" ~ start_date ~ "' as date)",
        end_date="cast('" ~ end_date ~ "' as date)"
        ) }}
    ) as spine
),
holidays as (
    select cast(date as date) as date, holiday_name
    from {{ ref('colombia_holidays') }}
),
-- Redshift no soporta extract(isodow from ...) (DuckDB sí). Redshift solo
-- tiene extract(dow from ...), que devuelve 0=domingo..6=sabado. Lo
-- convertimos acá una sola vez al estandar ISO (1=lunes..7=domingo) que
-- usaba el proyecto original.
with_iso_dow as (
    select
        date,
        case extract(dow from date)
            when 0 then 7
            else cast(extract(dow from date) as integer)
        end as day_of_week_number
    from date_spine
)

select
    {{ dbt_utils.generate_surrogate_key(['cast(date_spine.date as date)']) }} as date_sk,
    cast(date_spine.date as date) as date,
    cast(extract(year from date_spine.date) as integer) as year,
    cast(extract(quarter from date_spine.date) as integer) as quarter,
    cast(extract(month from date_spine.date) as integer) as month,
    cast(extract(week from date_spine.date) as integer) as week,
    with_iso_dow.day_of_week_number,
    case with_iso_dow.day_of_week_number
        when 1 then 'lunes'
        when 2 then 'martes'
        when 3 then 'miércoles'
        when 4 then 'jueves'
        when 5 then 'viernes'
        when 6 then 'sábado'
        when 7 then 'domingo'
    end as day_of_week,
    cast(extract(day from date_spine.date) as integer) as day_of_month,
    with_iso_dow.day_of_week_number in (6, 7) as is_weekend,
    holidays.holiday_name is not null as is_holiday,
    holidays.holiday_name as holiday_name
from date_spine
left join with_iso_dow on with_iso_dow.date = date_spine.date
left join holidays on holidays.date = date_spine.date
