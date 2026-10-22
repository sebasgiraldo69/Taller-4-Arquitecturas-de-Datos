output "data_lake_bucket_name" {
  description = "Nombre del bucket del Data Lake"
  value       = aws_s3_bucket.data_lake.bucket
}

output "data_lake_bucket_arn" {
  description = "ARN del bucket"
  value       = aws_s3_bucket.data_lake.arn
}
