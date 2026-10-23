variable "aws_region" {
  description = "Región AWS del Data Warehouse"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Nombre corto del proyecto, usado como prefijo de recursos"
  type        = string
  default     = "taller4-dw"
}

variable "bucket_name" {
  description = "Nombre globalmente único del bucket S3 (ajusta si ya existe)"
  type        = string
  default     = "taller4-datawarehouse-juanjo1414"
}

variable "allowed_cidr_blocks" {
  description = "IPs autorizadas a conectarse a las fuentes (tu IP pública en formato CIDR, ej. 190.1.2.3/32)"
  type        = list(string)
}

variable "mysql_database_name" {
  description = "Nombre de la base de datos MySQL inicial"
  type        = string
  default     = "ecommerce"
}

variable "mysql_master_username" {
  description = "Usuario maestro de RDS MySQL"
  type        = string
  default     = "etl"
}

variable "mysql_master_password" {
  description = "Contraseña del usuario maestro de RDS MySQL"
  type        = string
  sensitive   = true
}

variable "docdb_master_username" {
  description = "Usuario maestro de DocumentDB"
  type        = string
  default     = "etl"
}

variable "docdb_master_password" {
  description = "Contraseña del usuario maestro de DocumentDB (mínimo 8 caracteres)"
  type        = string
  sensitive   = true
}

variable "redshift_admin_username" {
  description = "Usuario administrador de Redshift Serverless"
  type        = string
  default     = "etl"
}

variable "redshift_admin_password" {
  description = "Contraseña del usuario administrador de Redshift Serverless (mínimo 8 caracteres, al menos 1 mayúscula, 1 minúscula y 1 número)"
  type        = string
  sensitive   = true
}