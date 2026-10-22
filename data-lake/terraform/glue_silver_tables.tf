locals {
  silver_bucket = "taller4-datalake-sebasgiraldo69"

  silver_publication_id = "1103d91dee05459ea95aadde13b4d9f0"

  silver_date = "year=2026/month=10/day=22"

  silver_publication_partition = "${local.silver_date}/run_id=${local.silver_publication_id}"
}

resource "aws_glue_catalog_table" "silver_news" {
  name          = "news"
  database_name = aws_glue_catalog_database.datalake.name
  table_type    = "EXTERNAL_TABLE"

  parameters = {
    EXTERNAL       = "TRUE"
    classification = "parquet"
  }

  storage_descriptor {
    location = "s3://${local.silver_bucket}/silver/news/${local.silver_date}/"

    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
    }

    columns {
      name = "news_id"
      type = "string"
    }

    columns {
      name = "title"
      type = "string"
    }

    columns {
      name = "description"
      type = "string"
    }

    columns {
      name = "url"
      type = "string"
    }

    columns {
      name = "section"
      type = "string"
    }

    columns {
      name = "source"
      type = "string"
    }

    columns {
      name = "published_at"
      type = "timestamp"
    }

    columns {
      name = "content_hash"
      type = "string"
    }

    columns {
      name = "ingestion_timestamp_utc"
      type = "timestamp"
    }

    columns {
      name = "year"
      type = "bigint"
    }

    columns {
      name = "month"
      type = "bigint"
    }

    columns {
      name = "day"
      type = "bigint"
    }
  }
}

resource "aws_glue_catalog_table" "silver_news_entities" {
  name          = "news_entities"
  database_name = aws_glue_catalog_database.datalake.name
  table_type    = "EXTERNAL_TABLE"

  parameters = {
    EXTERNAL       = "TRUE"
    classification = "parquet"
  }

  storage_descriptor {
    location = "s3://${local.silver_bucket}/silver/news_entities/${local.silver_publication_partition}/"

    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
    }

    columns {
      name = "news_id"
      type = "string"
    }

    columns {
      name = "content_hash"
      type = "string"
    }

    columns {
      name = "entity_text"
      type = "string"
    }

    columns {
      name = "entity_type"
      type = "string"
    }

    columns {
      name = "score"
      type = "double"
    }
  }
}

resource "aws_glue_catalog_table" "silver_news_key_phrases" {
  name          = "news_key_phrases"
  database_name = aws_glue_catalog_database.datalake.name
  table_type    = "EXTERNAL_TABLE"

  parameters = {
    EXTERNAL       = "TRUE"
    classification = "parquet"
  }

  storage_descriptor {
    location = "s3://${local.silver_bucket}/silver/news_key_phrases/${local.silver_publication_partition}/"

    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
    }

    columns {
      name = "news_id"
      type = "string"
    }

    columns {
      name = "content_hash"
      type = "string"
    }

    columns {
      name = "phrase_text"
      type = "string"
    }

    columns {
      name = "score"
      type = "double"
    }
  }
}
