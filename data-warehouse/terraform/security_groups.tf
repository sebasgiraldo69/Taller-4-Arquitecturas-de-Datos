resource "aws_security_group" "mysql" {
  name        = "${var.project_name}-mysql-sg"
  description = "Acceso a RDS MySQL (3306) desde IPs autorizadas"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "MySQL desde IPs autorizadas (tu maquina)"
    from_port   = 3306
    to_port     = 3306
    protocol    = "tcp"
    cidr_blocks = local.my_cidr
  }

  ingress {
    description     = "MySQL desde la EC2 de Airflow"
    from_port       = 3306
    to_port         = 3306
    protocol        = "tcp"
    security_groups = [aws_security_group.ec2.id]
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

resource "aws_security_group" "ec2" {
  name        = "${var.project_name}-ec2-sg"
  description = "Acceso SSH y UI de Airflow desde IPs autorizadas"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "SSH desde IPs autorizadas"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = local.my_cidr
  }

  ingress {
    description = "Airflow UI desde IPs autorizadas"
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    cidr_blocks = local.my_cidr
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

resource "aws_security_group" "documentdb" {
  name        = "${var.project_name}-docdb-sg"
  description = "Acceso a DocumentDB (27017) solo desde la EC2 de Airflow"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description     = "MongoDB/DocumentDB desde la EC2 de Airflow"
    from_port       = 27017
    to_port         = 27017
    protocol        = "tcp"
    security_groups = [aws_security_group.ec2.id]
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