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