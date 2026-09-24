# Free-tier data: latest Amazon Linux 2023 AMI, owned by Amazon.
data "aws_ami" "al2023" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

resource "aws_security_group" "app" {
  name        = "stackcx-app-sg"
  description = "Allow SSH (restricted), HTTP, HTTPS"

  ingress {
    description = "SSH from allowed CIDR only"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.allowed_ssh_cidr]
  }

  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "stackcx-app-sg"
  }
}

resource "aws_instance" "app" {
  ami                    = data.aws_ami.al2023.id
  instance_type          = var.instance_type
  key_name               = var.key_pair_name
  vpc_security_group_ids = [aws_security_group.app.id]

  # Installs Docker + Compose, clones the repo, brings the stack up.
  # Re-running `terraform apply` won't re-run this — it only fires on instance
  # creation. Deploys after the first boot go through the GitHub Actions
  # workflow (SSH + `git pull && docker compose up -d --build`), not Terraform.
  user_data = templatefile("${path.module}/user_data.sh.tftpl", {
    app_repo_url = var.app_repo_url
  })

  tags = {
    Name = "stackcx-assessment"
  }
}

resource "aws_eip" "app" {
  instance = aws_instance.app.id
  domain   = "vpc"

  tags = {
    Name = "stackcx-assessment"
  }
}
