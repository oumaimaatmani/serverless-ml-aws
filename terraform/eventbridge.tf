# =============================================================================
# EVENTBRIDGE CONFIGURATION
# Sets up event-driven triggers and notifications
# =============================================================================

# Custom event bus
resource "aws_cloudwatch_event_bus" "ml_processing" {
  name = "${local.project_name}-event-bus"

  tags = merge(local.common_tags, {
    Name        = "ML Processing Event Bus"
    Description = "Event bus for ML processing"
  })
}

# Rule 1: Trigger on S3 upload
resource "aws_cloudwatch_event_rule" "s3_upload" {
  name           = "${local.project_name}-s3-upload-rule"
  description    = "Detects new files uploaded to S3"
  event_bus_name = "default"

  event_pattern = jsonencode({
    source      = ["aws.s3"]
    detail-type = ["Object Created"]
    detail = {
      bucket = {
        name = [aws_s3_bucket.images_bucket.id]
      }
      object = {
        key = [
          {
            prefix = "uploads/"
          }
        ]
      }
    }
  })

  tags = merge(local.common_tags, {
    Name = "S3 Upload Detection Rule"
  })
}

# Target: Trigger Step Functions
resource "aws_cloudwatch_event_target" "trigger_step_functions" {
  rule           = aws_cloudwatch_event_rule.s3_upload.name
  arn            = aws_sfn_state_machine.image_processing_workflow.arn
  role_arn       = aws_iam_role.eventbridge_role.arn
  event_bus_name = "default"

  #Transform the s3 event to an input for the step functions
  input_transformer {
    input_paths = {
      bucket = "$.detail.bucket.name"
      key    = "$.detail.object.key"
      size   = "$.detail.object.size"
      time   = "$.time"
    }

    input_template = <<EOF
{
  "image_bucket": <bucket>,
  "image_key": <key>,
  "image_size": <size>,
  "upload_time": <time>,
  "workflow_trigger": "s3_upload"
}
EOF
  }
}

# Rule 2: Success events
resource "aws_cloudwatch_event_rule" "processing_success" {
  name           = "${local.project_name}-success-rule"
  description    = "Detects successful processing"
  event_bus_name = aws_cloudwatch_event_bus.ml_processing.name

  event_pattern = jsonencode({
    source      = ["custom.ml.processing"]
    detail-type = ["Image Processing Complete"]
    detail = {
      status = ["SUCCESS"]
    }
  })

  tags = merge(local.common_tags, {
    Name = "Processing Success Rule"
  })
}

resource "aws_cloudwatch_event_target" "log_success" {
  rule           = aws_cloudwatch_event_rule.processing_success.name
  arn            = aws_cloudwatch_log_group.processing_events.arn
  event_bus_name = aws_cloudwatch_event_bus.ml_processing.name
}

# Rule 3: Error events
resource "aws_cloudwatch_event_rule" "processing_error" {
  name           = "${local.project_name}-error-rule"
  description    = "Detects processing errors"
  event_bus_name = aws_cloudwatch_event_bus.ml_processing.name

  event_pattern = jsonencode({
    source      = ["custom.ml.processing"]
    detail-type = ["Image Processing Failed"]
    detail = {
      status = ["ERROR", "FAILED"]
    }
  })

  tags = merge(local.common_tags, {
    Name = "Processing Error Rule"
  })
}

resource "aws_cloudwatch_event_target" "notify_on_error" {
  rule           = aws_cloudwatch_event_rule.processing_error.name
  arn            = aws_lambda_function.notification_handler.arn
  event_bus_name = aws_cloudwatch_event_bus.ml_processing.name

  input_transformer {
    input_paths = {
      error_message = "$.detail.error_message"
      image_id      = "$.detail.image_id"
      timestamp     = "$.time"
    }

    input_template = <<EOF
{
  "notification_type": "error",
  "error_message": <error_message>,
  "image_id": <image_id>,
  "timestamp": <timestamp>
}
EOF
  }
}

resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.notification_handler.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.processing_error.arn
}

# Rule 4: Monitor Step Functions
resource "aws_cloudwatch_event_rule" "step_functions_status" {
  name        = "${local.project_name}-sfn-status-rule"
  description = "Monitors Step Functions execution state"

  event_pattern = jsonencode({
    source      = ["aws.states"]
    detail-type = ["Step Functions Execution Status Change"]
    detail = {
      stateMachineArn = [aws_sfn_state_machine.image_processing_workflow.arn]
      status          = ["FAILED", "TIMED_OUT", "ABORTED"]
    }
  })

  tags = merge(local.common_tags, {
    Name = "Step Functions Status Monitor"
  })
}

resource "aws_cloudwatch_event_target" "log_sfn_status" {
  rule = aws_cloudwatch_event_rule.step_functions_status.name
  arn  = aws_cloudwatch_log_group.step_functions_events.arn
}

# CloudWatch Log Groups
resource "aws_cloudwatch_log_group" "processing_events" {
  name              = "/aws/events/${local.project_name}-processing"
  retention_in_days = 7

  tags = merge(local.common_tags, {
    Name = "Processing Events Logs"
  })
}

resource "aws_cloudwatch_log_group" "step_functions_events" {
  name              = "/aws/events/${local.project_name}-stepfunctions"
  retention_in_days = 7

  tags = merge(local.common_tags, {
    Name = "Step Functions Events Logs"
  })
}

# Policy for EventBridge to write logs
data "aws_iam_policy_document" "eventbridge_logs_policy" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["events.amazonaws.com", "delivery.logs.amazonaws.com"]
    }

    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]

    resources = [
      "${aws_cloudwatch_log_group.processing_events.arn}:*",
      "${aws_cloudwatch_log_group.step_functions_events.arn}:*"
    ]
  }
}

resource "aws_cloudwatch_log_resource_policy" "eventbridge_logs" {
  policy_name     = "${local.project_name}-eventbridge-logs-policy"
  policy_document = data.aws_iam_policy_document.eventbridge_logs_policy.json
}

# Event archiving
resource "aws_cloudwatch_event_archive" "processing_archive" {
  name             = "${local.project_name}-events-archive"
  event_source_arn = aws_cloudwatch_event_bus.ml_processing.arn
  description      = "Archive of all ML processing events"
  retention_days   = 30

  event_pattern = jsonencode({
    source = ["custom.ml.processing"]
  })
}

# ===== OUTPUTS =====

output "event_bus_name" {
  description = "Name of custom event bus"
  value       = aws_cloudwatch_event_bus.ml_processing.name
}

output "event_bus_arn" {
  description = "ARN of event bus"
  value       = aws_cloudwatch_event_bus.ml_processing.arn
}

output "s3_upload_rule_name" {
  description = "Name of S3 upload detection rule"
  value       = aws_cloudwatch_event_rule.s3_upload.name
}
