resource "aws_key_pair" "ec2" {
  key_name   = "${var.project_name}-key"
  public_key = file("${path.module}/ec2_key.pub")
}

data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }
}

resource "aws_instance" "airflow" {
  ami                    = data.aws_ami.amazon_linux.id
  instance_type          = "t3.small"
  key_name               = aws_key_pair.ec2.key_name
  vpc_security_group_ids = [aws_security_group.ec2.id]
  subnet_id              = data.aws_subnets.default.ids[0]

  root_block_device {
    volume_size = 20
    volume_type = "gp3"
  }

  user_data = <<-EOF
    #!/bin/bash
    dnf update -y
    dnf install -y docker git mariadb105 python3-pip
    systemctl enable docker
    systemctl start docker
    usermod -aG docker ec2-user
    curl -SL https://github.com/docker/compose/releases/download/v2.29.7/docker-compose-linux-x86_64 -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    pip3 install pymongo
  EOF

  tags = {
    Name      = "${var.project_name}-airflow"
    Project   = "Taller4-DataWarehouse"
    ManagedBy = "Terraform"
  }
}