locals {
  gold_run_id = "7c51a5f63f11489180683efd1aa4f0a0"

  gold_partition = (
    "year=2026/month=10/day=22/run_id=${local.gold_run_id}"
  )

  gold_bucket = "taller4-datalake-sebasgiraldo69"
}

resource "aws_glue_catalog_table" "news_summary" {
  name          = "news_summary"
  database_name = aws_glue_catalog_database.datalake.name
  table_type    = "EXTERNAL_TABLE"

  parameters = {
    EXTERNAL              = "TRUE"
    classification        = "parquet"
    "parquet.compression" = "SNAPPY"
  }

  storage_descriptor {
    location = "s3://${local.gold_bucket}/gold/news_summary/${local.gold_partition}/"

    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
    }

    columns {
      name = "publication_date"
      type = "string"
    }

    columns {
      name = "section"
      type = "string"
    }

    columns {
      name = "news_count"
      type = "bigint"
    }
  }
}

resource "aws_glue_catalog_table" "top_entities" {
  name          = "top_entities"
  database_name = aws_glue_catalog_database.datalake.name
  table_type    = "EXTERNAL_TABLE"

  parameters = {
    EXTERNAL       = "TRUE"
    classification = "parquet"
  }

  storage_descriptor {
    location = "s3://${local.gold_bucket}/gold/top_entities/${local.gold_partition}/"

    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
    }

    columns {
      name = "section"
      type = "string"
    }

    columns {
      name = "entity_type"
      type = "string"
    }

    columns {
      name = "entity_text"
      type = "string"
    }

    columns {
      name = "mentions"
      type = "bigint"
    }

    columns {
      name = "news_count"
      type = "bigint"
    }

    columns {
      name = "avg_score"
      type = "double"
    }
  }
}

resource "aws_glue_catalog_table" "top_key_phrases" {
  name          = "top_key_phrases"
  database_name = aws_glue_catalog_database.datalake.name
  table_type    = "EXTERNAL_TABLE"

  parameters = {
    EXTERNAL       = "TRUE"
    classification = "parquet"
  }

  storage_descriptor {
    location = "s3://${local.gold_bucket}/gold/top_key_phrases/${local.gold_partition}/"

    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
    }

    columns {
      name = "section"
      type = "string"
    }

    columns {
      name = "phrase_text"
      type = "string"
    }

    columns {
      name = "mentions"
      type = "bigint"
    }

    columns {
      name = "news_count"
      type = "bigint"
    }

    columns {
      name = "avg_score"
      type = "double"
    }
  }
}
