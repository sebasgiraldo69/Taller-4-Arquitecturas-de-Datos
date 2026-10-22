resource "aws_s3_bucket" "data_warehouse" {
  bucket = var.bucket_name

  tags = {
    Project     = "Taller4-DataWarehouse"
    Environment = "Development"
    ManagedBy   = "Terraform"
  }
}

resource "aws_s3_bucket_public_access_block" "data_warehouse" {
  bucket = aws_s3_bucket.data_warehouse.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "data_warehouse" {
  bucket = aws_s3_bucket.data_warehouse.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_versioning" "data_warehouse" {
  bucket = aws_s3_bucket.data_warehouse.id

  versioning_configuration {
    status = "Enabled"
  }
}