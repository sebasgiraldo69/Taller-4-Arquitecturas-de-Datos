
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"]

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"]
  }

  filter {
    name   = "architecture"
    values = ["x86_64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

resource "aws_key_pair" "airflow" {
  key_name   = "taller4-airflow-key"
  public_key = file(pathexpand("~/.ssh/taller4_ec2.pub"))
}

resource "aws_security_group" "airflow" {
  name        = "taller4-airflow-sg"
  description = "Acceso SSH para Airflow EC2"

  ingress {
    description = "SSH desde IP autorizada"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.ssh_allowed_cidr]
  }

  egress {
    description = "Salida a Internet"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "taller4-airflow-sg"
  }
}

resource "aws_instance" "airflow" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = "t3.medium"
  key_name               = aws_key_pair.airflow.key_name
  vpc_security_group_ids = [aws_security_group.airflow.id]

  root_block_device {
    volume_size = 20
    volume_type = "gp3"
    encrypted   = true
  }

  metadata_options {
    http_tokens = "required"
  }

  tags = {
    Name = "taller4-airflow"
  }
}

variable "ssh_allowed_cidr" {
  description = "Direccion IP publica autorizada para SSH"
  type        = string
}

output "airflow_public_ip" {
  value = aws_instance.airflow.public_ip
}
