terraform {
  required_version = ">= 1.7"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Local state for this assessment — fine for solo/throwaway use.
  # For real/team use, switch to an S3 backend with DynamoDB state locking.
}

provider "aws" {
  region = var.aws_region
}
