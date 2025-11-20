# =============================================================================
# DYNAMODB TABLES CONFIGURATION
# Creates tables for storing analysis results and workflow logs
# =============================================================================

# Main table for image analysis results
resource "aws_dynamodb_table" "image_analysis_results" {
  name           = "${local.project_name}-analysis-results"
  billing_mode   = "PROVISIONED"
  read_capacity  = var.dynamodb_read_capacity
  write_capacity = var.dynamodb_write_capacity

  # Primary key: unique image ID
  hash_key = "image_id"

  # Sort key: processing timestamp
  range_key = "processed_timestamp"

  # Define attributes
  attribute {
    name = "image_id"
    type = "S"
  }

  attribute {
    name = "processed_timestamp"
    type = "N"
  }

  attribute {
    name = "user_id"
    type = "S"
  }

  # Global secondary index for querying by user
  global_secondary_index {
    name            = "UserIdIndex"
    hash_key        = "user_id"
    range_key       = "processed_timestamp"
    projection_type = "ALL"
    read_capacity   = var.dynamodb_read_capacity
    write_capacity  = var.dynamodb_write_capacity
  }

  # Enable TTL for automatic deletion
  ttl {
    attribute_name = "expiration_time"
    enabled        = true
  }

  # Enable point-in-time recovery
  point_in_time_recovery {
    enabled = true
  }

  # Enable encryption
  server_side_encryption {
    enabled = true
  }

  # Enable streams
  stream_enabled   = true
  stream_view_type = "NEW_AND_OLD_IMAGES"

  tags = merge(local.common_tags, {
    Name        = "Image Analysis Results"
    Description = "Stores ML analysis results"
  })
}

# Table for workflow execution logs
resource "aws_dynamodb_table" "workflow_logs" {
  name         = "${local.project_name}-workflow-logs"
  billing_mode = "PAY_PER_REQUEST"

  hash_key  = "execution_id"
  range_key = "step_timestamp"

  attribute {
    name = "execution_id"
    type = "S"
  }

  attribute {
    name = "step_timestamp"
    type = "N"
  }

  server_side_encryption {
    enabled = true
  }

  ttl {
    attribute_name = "expiration_time"
    enabled        = true
  }

  tags = merge(local.common_tags, {
    Name        = "Workflow Logs"
    Description = "Step Functions execution logs"
  })
}

# Outputs
output "dynamodb_analysis_table_name" {
  description = "Name of analysis results table"
  value       = aws_dynamodb_table.image_analysis_results.name
}

output "dynamodb_analysis_table_arn" {
  description = "ARN of analysis results table"
  value       = aws_dynamodb_table.image_analysis_results.arn
}

output "dynamodb_workflow_logs_table_name" {
  description = "Name of workflow logs table"
  value       = aws_dynamodb_table.workflow_logs.name
}
