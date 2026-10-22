resource "aws_docdb_subnet_group" "main" {
  name       = "${var.project_name}-docdb-subnet-group"
  subnet_ids = data.aws_subnets.default.ids

  tags = {
    Project   = "Taller4-DataWarehouse"
    ManagedBy = "Terraform"
  }
}

resource "aws_docdb_cluster" "main" {
  cluster_identifier = "${var.project_name}-docdb"
  engine              = "docdb"
  master_username     = var.docdb_master_username
  master_password     = var.docdb_master_password

  db_subnet_group_name   = aws_docdb_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.documentdb.id]

  storage_encrypted   = true
  skip_final_snapshot = true
  apply_immediately   = true

  tags = {
    Project   = "Taller4-DataWarehouse"
    ManagedBy = "Terraform"
  }
}

resource "aws_docdb_cluster_instance" "main" {
  identifier         = "${var.project_name}-docdb-instance-1"
  cluster_identifier = aws_docdb_cluster.main.id
  instance_class     = "db.t3.medium"

  tags = {
    Project   = "Taller4-DataWarehouse"
    ManagedBy = "Terraform"
  }
}