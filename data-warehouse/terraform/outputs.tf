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

output "mysql_endpoint" {
  description = "Endpoint (host:puerto) de RDS MySQL"
  value       = aws_db_instance.mysql.endpoint
}

output "ec2_public_ip" {
  description = "IP pública de la instancia EC2 de Airflow"
  value       = aws_instance.airflow.public_ip
}

output "ec2_ssh_command" {
  description = "Comando para conectarte por SSH a la instancia EC2"
  value       = "ssh -i ec2_key ec2-user@${aws_instance.airflow.public_ip}"
}

output "docdb_endpoint" {
  description = "Endpoint de escritura del clúster DocumentDB (solo accesible desde dentro de la VPC)"
  value       = aws_docdb_cluster.main.endpoint
}

output "docdb_port" {
  description = "Puerto de DocumentDB"
  value       = aws_docdb_cluster.main.port
}

output "redshift_workgroup_endpoint" {
  description = "Endpoint (host) del workgroup de Redshift Serverless"
  value       = aws_redshiftserverless_workgroup.main.endpoint[0].address
}

output "redshift_namespace_name" {
  description = "Nombre del namespace de Redshift Serverless"
  value       = aws_redshiftserverless_namespace.main.namespace_name
}

output "redshift_database_name" {
  description = "Nombre de la base de datos en Redshift"
  value       = aws_redshiftserverless_namespace.main.db_name
}