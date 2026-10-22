resource "aws_db_instance" "mysql" {
  identifier     = "${var.project_name}-mysql"
  engine         = "mysql"
  engine_version = "8.0"
  instance_class = "db.t3.micro"

  allocated_storage = 20
  storage_type      = "gp3"

  db_name  = var.mysql_database_name
  username = var.mysql_master_username
  password = var.mysql_master_password
  port     = 3306

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.mysql.id]
  publicly_accessible    = true

  multi_az            = false
  skip_final_snapshot = true
  deletion_protection = false
  apply_immediately   = true

  tags = {
    Project   = "Taller4-DataWarehouse"
    ManagedBy = "Terraform"
  }
}