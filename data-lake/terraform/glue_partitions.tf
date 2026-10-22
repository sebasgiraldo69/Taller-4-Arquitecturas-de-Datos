resource "aws_glue_catalog_table" "news_partitioned" {
  name          = "news_partitioned"
  database_name = aws_glue_catalog_database.datalake.name
  table_type    = "EXTERNAL_TABLE"

  parameters = {
    EXTERNAL       = "TRUE"
    classification = "parquet"
  }

  storage_descriptor {
    location = "s3://${aws_s3_bucket.data_lake.bucket}/silver/news/"

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
  }

  partition_keys {
    name = "year"
    type = "bigint"
  }

  partition_keys {
    name = "month"
    type = "bigint"
  }

  partition_keys {
    name = "day"
    type = "bigint"
  }
}

resource "aws_glue_partition" "news_2026_10_22" {
  database_name = aws_glue_catalog_database.datalake.name
  table_name    = aws_glue_catalog_table.news_partitioned.name

  partition_values = ["2026", "10", "22"]

  storage_descriptor {
    location = "s3://${aws_s3_bucket.data_lake.bucket}/silver/news/year=2026/month=10/day=22/"

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
  }
}
