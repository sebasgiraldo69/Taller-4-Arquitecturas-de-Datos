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

# Rol que asume la propia instancia EC2 (vía su instance profile), para que los
# contenedores de Airflow puedan leer/escribir S3 sin credenciales estáticas.
resource "aws_iam_role" "ec2_s3_access" {
  name = "${var.project_name}-ec2-s3-access"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
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

resource "aws_iam_role_policy" "ec2_s3_read_write" {
  name = "${var.project_name}-ec2-s3-read-write"
  role = aws_iam_role.ec2_s3_access.id

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
        Action   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"]
        Resource = ["${aws_s3_bucket.data_warehouse.arn}/*"]
      }
    ]
  })
}

resource "aws_iam_instance_profile" "ec2" {
  name = "${var.project_name}-ec2-profile"
  role = aws_iam_role.ec2_s3_access.name
}