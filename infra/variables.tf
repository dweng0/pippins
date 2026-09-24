variable "aws_region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "eu-north-1"
}

variable "instance_type" {
  description = "Free-tier eligible instance type"
  type        = string
  default     = "t3.micro"
}

variable "key_pair_name" {
  description = "Name of the EC2 key pair created manually in the console (infra/README.md step 6)"
  type        = string
  default     = "stackcx-assessment"
}

variable "app_repo_url" {
  description = "GitHub repo URL the instance pulls on boot"
  type        = string
}
