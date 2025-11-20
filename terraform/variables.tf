# =============================================================================
# VARIABLES DEFINITION
# All configurable parameters for the project
# =============================================================================

variable "aws_region" {
  description = "AWS region where infrastructure will be deployed"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

variable "lambda_memory_size" {
  description = "Memory allocated to Lambda functions in MB"
  type        = number
  default     = 512
}

variable "lambda_timeout" {
  description = "Timeout for Lambda functions in seconds"
  type        = number
  default     = 60
}

variable "dynamodb_read_capacity" {
  description = "DynamoDB read capacity units"
  type        = number
  default     = 5
}

variable "dynamodb_write_capacity" {
  description = "DynamoDB write capacity units"
  type        = number
  default     = 5
}

variable "rekognition_confidence_threshold" {
  description = "Minimum confidence threshold for Rekognition (0-100)"
  type        = number
  default     = 80

  validation {
    condition     = var.rekognition_confidence_threshold >= 0 && var.rekognition_confidence_threshold <= 100
    error_message = "Threshold must be between 0 and 100."
  }
}

variable "notification_email" {
  description = "Email address for notifications (optional)"
  type        = string
  default     = ""
}

variable "additional_tags" {
  description = "Additional tags to apply to resources"
  type        = map(string)
  default     = {}
}
