resource "aws_athena_workgroup" "datalake" {
  name        = "taller4_datalake"
  description = "Consultas SQL del Data Lake de noticias"

  state = "ENABLED"

  configuration {
    enforce_workgroup_configuration    = true
    publish_cloudwatch_metrics_enabled = true

    bytes_scanned_cutoff_per_query = 10485760

    result_configuration {
      output_location       = "s3://${aws_s3_bucket.data_lake.bucket}/athena-results/"
      expected_bucket_owner = "211107604485"

      encryption_configuration {
        encryption_option = "SSE_S3"
      }
    }
  }
}

