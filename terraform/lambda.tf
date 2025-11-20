# =============================================================================
# LAMBDA FUNCTIONS CONFIGURATION
# Deploys all 5 Lambda functions + API Gateway
# =============================================================================

# ===== LAMBDA 1: IMAGE PROCESSOR =====

data "archive_file" "image_processor" {
  type        = "zip"
  source_dir  = "${path.module}/../backend/lambdas/image_processor"
  output_path = "${path.module}/lambda_packages/image_processor.zip"
}

resource "aws_lambda_function" "image_processor" {
  filename         = data.archive_file.image_processor.output_path
  function_name    = "${local.project_name}-image-processor"
  role             = aws_iam_role.lambda_execution_role.arn
  handler          = "lambda_function.lambda_handler"
  source_code_hash = data.archive_file.image_processor.output_base64sha256
  runtime          = "python3.11"
  timeout          = var.lambda_timeout
  memory_size      = var.lambda_memory_size

  environment {
    variables = {
      ENVIRONMENT    = var.environment
      IMAGES_BUCKET  = aws_s3_bucket.images_bucket.id
      DYNAMODB_TABLE = aws_dynamodb_table.image_analysis_results.name
      LOG_LEVEL      = "INFO"
    }
  }

  tracing_config {
    mode = "Active"
  }

  tags = merge(local.common_tags, {
    Name        = "Image Processor"
    Description = "Validates and prepares images"
  })
}

resource "aws_cloudwatch_log_group" "image_processor" {
  name              = "/aws/lambda/${aws_lambda_function.image_processor.function_name}"
  retention_in_days = 14

  tags = local.common_tags
}

# ===== LAMBDA 2: REKOGNITION ANALYZER =====

data "archive_file" "rekognition_analyzer" {
  type        = "zip"
  source_dir  = "${path.module}/../backend/lambdas/rekognition_analyzer"
  output_path = "${path.module}/lambda_packages/rekognition_analyzer.zip"
}

resource "aws_lambda_function" "rekognition_analyzer" {
  filename         = data.archive_file.rekognition_analyzer.output_path
  function_name    = "${local.project_name}-rekognition-analyzer"
  role             = aws_iam_role.lambda_execution_role.arn
  handler          = "lambda_function.lambda_handler"
  source_code_hash = data.archive_file.rekognition_analyzer.output_base64sha256
  runtime          = "python3.11"
  timeout          = 120
  memory_size      = 1024

  environment {
    variables = {
      ENVIRONMENT          = var.environment
      IMAGES_BUCKET        = aws_s3_bucket.images_bucket.id
      CONFIDENCE_THRESHOLD = var.rekognition_confidence_threshold
      LOG_LEVEL            = "INFO"
    }
  }

  tracing_config {
    mode = "Active"
  }

  tags = merge(local.common_tags, {
    Name        = "Rekognition Analyzer"
    Description = "ML analysis with Rekognition"
  })
}

resource "aws_cloudwatch_log_group" "rekognition_analyzer" {
  name              = "/aws/lambda/${aws_lambda_function.rekognition_analyzer.function_name}"
  retention_in_days = 14

  tags = local.common_tags
}

# ===== LAMBDA 3: RESULT SAVER =====

data "archive_file" "result_saver" {
  type        = "zip"
  source_dir  = "${path.module}/../backend/lambdas/result_saver"
  output_path = "${path.module}/lambda_packages/result_saver.zip"
}

resource "aws_lambda_function" "result_saver" {
  filename         = data.archive_file.result_saver.output_path
  function_name    = "${local.project_name}-result-saver"
  role             = aws_iam_role.lambda_execution_role.arn
  handler          = "lambda_function.lambda_handler"
  source_code_hash = data.archive_file.result_saver.output_base64sha256
  runtime          = "python3.11"
  timeout          = var.lambda_timeout
  memory_size      = var.lambda_memory_size

  environment {
    variables = {
      ENVIRONMENT        = var.environment
      DYNAMODB_TABLE     = aws_dynamodb_table.image_analysis_results.name
      WORKFLOW_LOG_TABLE = aws_dynamodb_table.workflow_logs.name
      LOG_LEVEL          = "INFO"
    }
  }

  tracing_config {
    mode = "Active"
  }

  tags = merge(local.common_tags, {
    Name        = "Result Saver"
    Description = "Saves results to DynamoDB"
  })
}

resource "aws_cloudwatch_log_group" "result_saver" {
  name              = "/aws/lambda/${aws_lambda_function.result_saver.function_name}"
  retention_in_days = 14

  tags = local.common_tags
}

# ===== LAMBDA 4: NOTIFICATION HANDLER =====

data "archive_file" "notification_handler" {
  type        = "zip"
  source_dir  = "${path.module}/../backend/lambdas/notification_handler"
  output_path = "${path.module}/lambda_packages/notification_handler.zip"
}

resource "aws_lambda_function" "notification_handler" {
  filename         = data.archive_file.notification_handler.output_path
  function_name    = "${local.project_name}-notification-handler"
  role             = aws_iam_role.lambda_execution_role.arn
  handler          = "lambda_function.lambda_handler"
  source_code_hash = data.archive_file.notification_handler.output_base64sha256
  runtime          = "python3.11"
  timeout          = var.lambda_timeout
  memory_size      = var.lambda_memory_size

  environment {
    variables = {
      ENVIRONMENT        = var.environment
      NOTIFICATION_EMAIL = var.notification_email
      LOG_LEVEL          = "INFO"
    }
  }

  tracing_config {
    mode = "Active"
  }

  tags = merge(local.common_tags, {
    Name        = "Notification Handler"
    Description = "Handles notifications"
  })
}

resource "aws_cloudwatch_log_group" "notification_handler" {
  name              = "/aws/lambda/${aws_lambda_function.notification_handler.function_name}"
  retention_in_days = 14

  tags = local.common_tags
}

# =============================================================================
# LAMBDA 5: PRESIGNED URL GENERATOR (Upload API)
# =============================================================================

data "archive_file" "presigned_url_generator_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../backend/lambdas/presigned_url_generator"
  output_path = "${path.module}/lambda_packages/presigned_url_generator.zip"
}

resource "aws_lambda_function" "presigned_url_generator" {
  filename         = data.archive_file.presigned_url_generator_zip.output_path
  function_name    = "${local.project_name}-presigned-url-generator"
  role             = aws_iam_role.lambda_presigned_url_role.arn
  handler          = "lambda_function.lambda_handler"
  source_code_hash = data.archive_file.presigned_url_generator_zip.output_base64sha256
  runtime          = "python3.11"
  timeout          = 30
  memory_size      = 256

  environment {
    variables = {
      IMAGES_BUCKET            = aws_s3_bucket.images_bucket.id
      PRESIGNED_URL_EXPIRATION = "300"
      LOG_LEVEL                = "INFO"
    }
  }

  tags = merge(local.common_tags, {
    Name        = "Presigned URL Generator"
    Description = "Generate presigned S3 URLs for uploads"
  })

  depends_on = [aws_iam_role_policy.lambda_presigned_url_policy]
}

resource "aws_cloudwatch_log_group" "presigned_url_generator" {
  name              = "/aws/lambda/${aws_lambda_function.presigned_url_generator.function_name}"
  retention_in_days = 14

  tags = local.common_tags
}

# IAM Role for Presigned URL Generator
resource "aws_iam_role" "lambda_presigned_url_role" {
  name = "${local.project_name}-lambda-presigned-url-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "lambda_presigned_url_basic" {
  role       = aws_iam_role.lambda_presigned_url_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "lambda_presigned_url_policy" {
  name = "${local.project_name}-lambda-presigned-url-policy"
  role = aws_iam_role.lambda_presigned_url_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:PutObjectAcl"
        ]
        Resource = "${aws_s3_bucket.images_bucket.arn}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      }
    ]
  })
}

# =============================================================================
# LAMBDA 6: RESULT VIEWER (Query API)
# =============================================================================

data "archive_file" "result_viewer_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../backend/lambdas/result_viewer"
  output_path = "${path.module}/lambda_packages/result_viewer.zip"
}

resource "aws_lambda_function" "result_viewer" {
  filename         = data.archive_file.result_viewer_zip.output_path
  function_name    = "${local.project_name}-result-viewer"
  role             = aws_iam_role.lambda_result_viewer_role.arn
  handler          = "lambda_function.lambda_handler"
  source_code_hash = data.archive_file.result_viewer_zip.output_base64sha256
  runtime          = "python3.11"
  timeout          = 30
  memory_size      = 256

  environment {
    variables = {
      DYNAMODB_TABLE = aws_dynamodb_table.image_analysis_results.name
      LOG_LEVEL      = "INFO"
    }
  }

  tags = merge(local.common_tags, {
    Name        = "Result Viewer"
    Description = "Query analysis results from API"
  })

  depends_on = [aws_iam_role_policy.lambda_result_viewer_policy]
}

resource "aws_cloudwatch_log_group" "result_viewer" {
  name              = "/aws/lambda/${aws_lambda_function.result_viewer.function_name}"
  retention_in_days = 14

  tags = local.common_tags
}

# =============================================================================
# IAM ROLE FOR RESULT VIEWER LAMBDA
# =============================================================================

resource "aws_iam_role" "lambda_result_viewer_role" {
  name = "${local.project_name}-lambda-result-viewer-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "lambda_result_viewer_basic" {
  role       = aws_iam_role.lambda_result_viewer_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "lambda_result_viewer_policy" {
  name = "${local.project_name}-lambda-result-viewer-policy"
  role = aws_iam_role.lambda_result_viewer_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:Scan",
          "dynamodb:Query"
        ]
        Resource = [
          aws_dynamodb_table.image_analysis_results.arn,
          "${aws_dynamodb_table.image_analysis_results.arn}/index/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      }
    ]
  })
}

# =============================================================================
# API GATEWAY FOR RESULT VIEWER
# =============================================================================

resource "aws_apigatewayv2_api" "results_api" {
  name          = "${local.project_name}-results-api"
  protocol_type = "HTTP"

  cors_configuration {
    allow_origins = ["*"]
    allow_methods = ["GET", "POST", "OPTIONS"]
    allow_headers = ["Content-Type", "Authorization"]
  }

  tags = local.common_tags
}

resource "aws_apigatewayv2_stage" "results_api_stage" {
  api_id      = aws_apigatewayv2_api.results_api.id
  name        = "prod"
  auto_deploy = true

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_gateway_logs.arn
    format = jsonencode({
      requestId      = "$context.requestId"
      ip             = "$context.identity.sourceIp"
      requestTime    = "$context.requestTime"
      httpMethod     = "$context.httpMethod"
      resourcePath   = "$context.resourcePath"
      status         = "$context.status"
      protocol       = "$context.protocol"
      responseLength = "$context.responseLength"
    })
  }

  tags = local.common_tags
}

resource "aws_cloudwatch_log_group" "api_gateway_logs" {
  name              = "/aws/apigateway/${local.project_name}-results-api"
  retention_in_days = 14

  tags = local.common_tags
}

# Integration for POST /upload-url (presigned URL generation)
resource "aws_apigatewayv2_integration" "upload_url_post" {
  api_id           = aws_apigatewayv2_api.results_api.id
  integration_type = "AWS_PROXY"

  integration_method     = "POST"
  integration_uri        = aws_lambda_function.presigned_url_generator.invoke_arn
  payload_format_version = "2.0"
}

# Integration for GET /results (all results)
resource "aws_apigatewayv2_integration" "results_get_all" {
  api_id           = aws_apigatewayv2_api.results_api.id
  integration_type = "AWS_PROXY"

  integration_method     = "POST"
  integration_uri        = aws_lambda_function.result_viewer.invoke_arn
  payload_format_version = "2.0"
}

# Integration for GET /results/{image_id} (specific result)
resource "aws_apigatewayv2_integration" "results_get_by_id" {
  api_id           = aws_apigatewayv2_api.results_api.id
  integration_type = "AWS_PROXY"

  integration_method     = "POST"
  integration_uri        = aws_lambda_function.result_viewer.invoke_arn
  payload_format_version = "2.0"
}

# Route for POST /upload-url
resource "aws_apigatewayv2_route" "post_upload_url" {
  api_id    = aws_apigatewayv2_api.results_api.id
  route_key = "POST /upload-url"
  target    = "integrations/${aws_apigatewayv2_integration.upload_url_post.id}"
}

# Route for GET /results
resource "aws_apigatewayv2_route" "get_all_results" {
  api_id    = aws_apigatewayv2_api.results_api.id
  route_key = "GET /results"
  target    = "integrations/${aws_apigatewayv2_integration.results_get_all.id}"
}

# Route for GET /results/{image_id}
resource "aws_apigatewayv2_route" "get_result_by_id" {
  api_id    = aws_apigatewayv2_api.results_api.id
  route_key = "GET /results/{image_id}"
  target    = "integrations/${aws_apigatewayv2_integration.results_get_by_id.id}"
}

# Permission for API Gateway to invoke Result Viewer Lambda
resource "aws_lambda_permission" "api_gateway_invoke_result_viewer" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.result_viewer.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.results_api.execution_arn}/*/*"
}

# Permission for API Gateway to invoke Presigned URL Generator Lambda
resource "aws_lambda_permission" "api_gateway_invoke_presigned_url" {
  statement_id  = "AllowAPIGatewayInvokePresignedUrl"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.presigned_url_generator.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.results_api.execution_arn}/*/*"
}

# =============================================================================
# OUTPUTS
# =============================================================================

output "lambda_image_processor_arn" {
  description = "ARN of Image Processor Lambda"
  value       = aws_lambda_function.image_processor.arn
}

output "lambda_rekognition_analyzer_arn" {
  description = "ARN of Rekognition Analyzer Lambda"
  value       = aws_lambda_function.rekognition_analyzer.arn
}

output "lambda_result_saver_arn" {
  description = "ARN of Result Saver Lambda"
  value       = aws_lambda_function.result_saver.arn
}

output "lambda_notification_handler_arn" {
  description = "ARN of Notification Handler Lambda"
  value       = aws_lambda_function.notification_handler.arn
}

output "lambda_result_viewer_arn" {
  description = "ARN of Result Viewer Lambda"
  value       = aws_lambda_function.result_viewer.arn
}

output "api_gateway_url" {
  description = "API Gateway endpoint URL"
  value       = "${aws_apigatewayv2_api.results_api.api_endpoint}/prod"
}

output "api_gateway_endpoints" {
  description = "Available API endpoints"
  value = {
    upload_url      = "${aws_apigatewayv2_api.results_api.api_endpoint}/prod/upload-url"
    get_all_results = "${aws_apigatewayv2_api.results_api.api_endpoint}/prod/results"
    get_by_id       = "${aws_apigatewayv2_api.results_api.api_endpoint}/prod/results/{image_id}"
  }
}

output "lambda_presigned_url_generator_arn" {
  description = "ARN of Presigned URL Generator Lambda"
  value       = aws_lambda_function.presigned_url_generator.arn
}
