# =============================================================================
# STEP FUNCTIONS STATE MACHINE
# Orchestrates the image processing workflow
# =============================================================================

resource "aws_cloudwatch_log_group" "step_functions" {
  name              = "/aws/states/${local.project_name}-workflow"
  retention_in_days = 14

  tags = local.common_tags
}

resource "aws_sfn_state_machine" "image_processing_workflow" {
  name     = "${local.project_name}-image-workflow"
  role_arn = aws_iam_role.step_functions_role.arn

  definition = jsonencode({
    Comment = "Image processing workflow with ML"
    StartAt = "ValidateImage"

    States = {
      ValidateImage = {
        Type     = "Task"
        Resource = aws_lambda_function.image_processor.arn
        Comment  = "Validates image format and size"

        Retry = [
          {
            ErrorEquals = [
              "States.TaskFailed",
              "Lambda.ServiceException",
              "Lambda.TooManyRequestsException"
            ]
            IntervalSeconds = 2
            MaxAttempts     = 3
            BackoffRate     = 2.0
          }
        ]

        Catch = [
          {
            ErrorEquals = ["ValidationError"]
            ResultPath  = "$.error"
            Next        = "ValidationFailed"
          },
          {
            ErrorEquals = ["States.ALL"]
            ResultPath  = "$.error"
            Next        = "HandleError"
          }
        ]

        TimeoutSeconds = 60
        Next           = "AnalyzeWithRekognition"
      }

      AnalyzeWithRekognition = {
        Type     = "Task"
        Resource = aws_lambda_function.rekognition_analyzer.arn
        Comment  = "Analyzes image with Rekognition"

        ResultPath = "$.analysis"

        Retry = [
          {
            ErrorEquals = [
              "States.TaskFailed",
              "Lambda.ServiceException",
              "Rekognition.ServiceException"
            ]
            IntervalSeconds = 3
            MaxAttempts     = 2
            BackoffRate     = 2.0
          }
        ]

        Catch = [
          {
            ErrorEquals = ["States.ALL"]
            ResultPath  = "$.error"
            Next        = "HandleError"
          }
        ]

        TimeoutSeconds = 120
        Next           = "CheckConfidence"
      }

      CheckConfidence = {
        Type    = "Choice"
        Comment = "Checks confidence level"

        Choices = [
          {
            Variable                 = "$.analysis.confidence"
            NumericGreaterThanEquals = 80
            Next                     = "SaveResults"
          }
        ]

        Default = "LowConfidenceWarning"
      }

      LowConfidenceWarning = {
        Type    = "Pass"
        Comment = "Marks results as uncertain"

        Result = {
          warning = "Low confidence results"
        }

        ResultPath = "$.warning"
        Next       = "SaveResults"
      }

      SaveResults = {
        Type     = "Task"
        Resource = aws_lambda_function.result_saver.arn
        Comment  = "Saves results to DynamoDB"

        ResultPath = "$.save_result"

        Retry = [
          {
            ErrorEquals = [
              "States.TaskFailed",
              "DynamoDB.ServiceException"
            ]
            IntervalSeconds = 1
            MaxAttempts     = 3
            BackoffRate     = 2.0
          }
        ]

        Catch = [
          {
            ErrorEquals = ["States.ALL"]
            ResultPath  = "$.error"
            Next        = "HandleError"
          }
        ]

        TimeoutSeconds = 60
        Next           = "ParallelNotifications"
      }

      ParallelNotifications = {
        Type    = "Parallel"
        Comment = "Sends notifications in parallel"

        Branches = [
          {
            StartAt = "SendNotification"
            States = {
              SendNotification = {
                Type     = "Task"
                Resource = aws_lambda_function.notification_handler.arn
                Comment  = "Sends EventBridge notification"

                Parameters = {
                  "notification_type" = "success"
                  "data.$"            = "$"
                }

                End = true
              }
            }
          },
          {
            StartAt = "LogSuccess"
            States = {
              LogSuccess = {
                Type    = "Pass"
                Comment = "Logs processing success"

                Result = {
                  status    = "SUCCESS"
                  timestamp = "$.timestamp"
                }

                End = true
              }
            }
          }
        ]

        Next = "ProcessingComplete"
      }

      ProcessingComplete = {
        Type    = "Succeed"
        Comment = "Image processing completed successfully"
      }

      ValidationFailed = {
        Type     = "Task"
        Resource = aws_lambda_function.notification_handler.arn
        Comment  = "Notifies validation failure"

        Parameters = {
          "notification_type" = "validation_failed"
          "error.$"           = "$.error"
        }

        Next = "ProcessingFailed"
      }

      HandleError = {
        Type     = "Task"
        Resource = aws_lambda_function.notification_handler.arn
        Comment  = "Handles workflow errors"

        Parameters = {
          "notification_type" = "error"
          "error.$"           = "$.error"
        }

        Next = "ProcessingFailed"
      }

      ProcessingFailed = {
        Type  = "Fail"
        Cause = "Image processing workflow failed"
        Error = "WorkflowError"
      }
    }
  })

  logging_configuration {
    log_destination        = "${aws_cloudwatch_log_group.step_functions.arn}:*"
    include_execution_data = true
    level                  = "ALL"
  }

  tracing_configuration {
    enabled = true
  }

  tags = merge(local.common_tags, {
    Name        = "Image Processing Workflow"
    Description = "Orchestrates ML image processing"
  })
}

# ===== OUTPUTS =====

output "step_functions_arn" {
  description = "ARN of Step Functions state machine"
  value       = aws_sfn_state_machine.image_processing_workflow.arn
}

output "step_functions_name" {
  description = "Name of state machine"
  value       = aws_sfn_state_machine.image_processing_workflow.name
}

output "step_functions_dashboard_url" {
  description = "URL to Step Functions dashboard"
  value       = "https://console.aws.amazon.com/states/home?region=${var.aws_region}#/statemachines/view/${aws_sfn_state_machine.image_processing_workflow.arn}"
}
