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

# Cloudflare's published edge ranges. Web traffic must come through the Cloudflare proxy,
# so the raw instance IP doesn't serve the site.
data "http" "cloudflare_ipv4" {
  url = "https://www.cloudflare.com/ips-v4"
}

locals {
  cloudflare_ipv4 = split("\n", trimspace(data.http.cloudflare_ipv4.response_body))
}

# No SSH ingress: shell access is via SSM Session Manager (IAM-authenticated, outbound-only).
resource "aws_security_group" "app" {
  name = "stackcx-app-sg"
  # Stale wording, kept on purpose: changing a security group's description forces replacement.
  description = "Allow SSH (restricted), HTTP, HTTPS"

  ingress {
    description = "HTTP from Cloudflare only"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = local.cloudflare_ipv4
  }

  ingress {
    description = "HTTPS from Cloudflare only"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = local.cloudflare_ipv4
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

# Instance role: only what the SSM agent needs for Session Manager.
resource "aws_iam_role" "app" {
  name = "stackcx-app"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ssm" {
  role       = aws_iam_role.app.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_instance_profile" "app" {
  name = "stackcx-app"
  role = aws_iam_role.app.name
}

resource "aws_instance" "app" {
  ami                    = data.aws_ami.al2023.id
  instance_type          = var.instance_type
  key_name               = var.key_pair_name
  vpc_security_group_ids = [aws_security_group.app.id]
  iam_instance_profile   = aws_iam_instance_profile.app.name

  # IMDSv2 only; hop limit 1 keeps Docker containers (one hop further) away from the
  # instance role's credentials.
  metadata_options {
    http_tokens                 = "required"
    http_put_response_hop_limit = 1
  }

  # Installs Docker + Compose, swap, clones the repo, installs the pull-based deploy timer.
  # Only fires on instance creation. Later deploys are done by that timer (infra/deploy.sh),
  # not by Terraform or inbound SSH.
  user_data = templatefile("${path.module}/user_data.sh.tftpl", {
    app_repo_url = var.app_repo_url
  })

  # user_data only runs on first boot; editing the template must not restart the box.
  # ami: the data source above resolves to each newly published AMI, and ami forces replacement,
  # which would wipe Postgres on the root volume. Roll the AMI deliberately instead.
  lifecycle {
    ignore_changes = [user_data, ami]
  }

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
