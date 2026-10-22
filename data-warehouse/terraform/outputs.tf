output "data_warehouse_bucket_name" {
  description = "Nombre del bucket raw del Data Warehouse"
  value       = aws_s3_bucket.data_warehouse.bucket
}

output "data_warehouse_bucket_arn" {
  description = "ARN del bucket"
  value       = aws_s3_bucket.data_warehouse.arn
}

output "redshift_s3_role_arn" {
  description = "ARN del rol IAM que Redshift asumirá para hacer COPY desde S3"
  value       = aws_iam_role.redshift_s3_access.arn
}