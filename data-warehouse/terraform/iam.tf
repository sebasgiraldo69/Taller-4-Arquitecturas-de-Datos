# "assume role policy" = quién puede USAR este rol (aquí: el servicio Redshift).
resource "aws_iam_role" "redshift_s3_access" {
  name = "${var.project_name}-redshift-s3-access"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "redshift.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = {
    Project   = "Taller4-DataWarehouse"
    ManagedBy = "Terraform"
  }
}

# Política que define QUÉ puede hacer el rol: leer/listar/escribir el bucket raw.
resource "aws_iam_role_policy" "redshift_s3_read" {
  name = "${var.project_name}-redshift-s3-read"
  role = aws_iam_role.redshift_s3_access.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "ListBucket"
        Effect   = "Allow"
        Action   = ["s3:ListBucket"]
        Resource = [aws_s3_bucket.data_warehouse.arn]
      },
      {
        Sid      = "ReadWriteObjects"
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:PutObject"]
        Resource = ["${aws_s3_bucket.data_warehouse.arn}/*"]
      }
    ]
  })
}