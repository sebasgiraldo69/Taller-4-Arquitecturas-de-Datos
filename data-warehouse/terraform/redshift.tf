resource "aws_security_group" "redshift" {
  name        = "${var.project_name}-redshift-sg"
  description = "Acceso a Redshift Serverless (5439) desde IPs autorizadas y la EC2 de Airflow"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "Redshift desde IPs autorizadas (tu maquina)"
    from_port   = 5439
    to_port     = 5439
    protocol    = "tcp"
    cidr_blocks = local.my_cidr
  }

  ingress {
    description     = "Redshift desde la EC2 de Airflow"
    from_port       = 5439
    to_port         = 5439
    protocol        = "tcp"
    security_groups = [aws_security_group.ec2.id]
  }

  ingress {
    # Rango publicado por AWS para QuickSight en us-east-1 (conexion de red publica a origenes de datos):
    # https://docs.aws.amazon.com/quicksight/latest/user/regions.html
    description = "Redshift desde Amazon QuickSight (us-east-1)"
    from_port   = 5439
    to_port     = 5439
    protocol    = "tcp"
    cidr_blocks = ["52.23.63.224/27"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Project   = "Taller4-DataWarehouse"
    ManagedBy = "Terraform"
  }
}

resource "aws_redshiftserverless_namespace" "main" {
  namespace_name = "${var.project_name}-ns"
  db_name        = "ecommerce_dw"

  admin_username      = var.redshift_admin_username
  admin_user_password = var.redshift_admin_password

  iam_roles            = [aws_iam_role.redshift_s3_access.arn]
  default_iam_role_arn = aws_iam_role.redshift_s3_access.arn

  tags = {
    Project   = "Taller4-DataWarehouse"
    ManagedBy = "Terraform"
  }
}

resource "aws_redshiftserverless_workgroup" "main" {
  namespace_name = aws_redshiftserverless_namespace.main.namespace_name
  workgroup_name = "${var.project_name}-wg"

  base_capacity = 8

  publicly_accessible = true
  subnet_ids          = data.aws_subnets.default.ids
  security_group_ids  = [aws_security_group.redshift.id]

  tags = {
    Project   = "Taller4-DataWarehouse"
    ManagedBy = "Terraform"
  }
}