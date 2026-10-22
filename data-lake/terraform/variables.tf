variable "aws_region" {
  description = "Region AWS del Data Lake"
  type        = string
  default     = "us-east-1"
}

variable "bucket_name" {
  description = "Nombre globalmente unico del bucket S3"
  type        = string
  default     = "taller4-datalake-sebasgiraldo69"
}
