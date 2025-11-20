# =============================================================================
# MAIN CONFIGURATION FILE
# This file configures the AWS provider and creates the S3 bucket
# =============================================================================

# AWS Provider configuration
provider "aws" {
  region  = var.aws_region
  profile = "terraform_oh"
  # Default tags applied to all resources
  default_tags {
    tags = {
      Project     = "ServerlessML"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}

# Local variables for reuse across files
locals {
  project_name = "serverless-ml-${var.environment}"

  common_tags = {
    Project     = "ServerlessML"
    Environment = var.environment
  }
}

# Random ID for unique bucket name
resource "random_id" "bucket_suffix" {
  byte_length = 4
}