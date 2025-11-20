# =============================================================================
# IAM ROLES AND POLICIES
# Defines permissions for Lambda, Step Functions, and EventBridge
# =============================================================================

# ===== LAMBDA IAM ROLE =====

data "aws_iam_policy_document" "lambda_assume_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "lambda_execution_role" {
  name               = "${local.project_name}-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json

  tags = merge(local.common_tags, {
    Name = "Lambda Execution Role"
  })
}

# Attach basic execution policy
resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.lambda_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# S3 access policy
data "aws_iam_policy_document" "lambda_s3_access" {
  statement {
    effect = "Allow"

    actions = [
      "s3:GetObject",
      "s3:GetObjectVersion",
      "s3:PutObject",
      "s3:ListBucket"
    ]

    resources = [
      aws_s3_bucket.images_bucket.arn,
      "${aws_s3_bucket.images_bucket.arn}/*"
    ]
  }
}

resource "aws_iam_policy" "lambda_s3_policy" {
  name        = "${local.project_name}-lambda-s3-policy"
  description = "Allows Lambda to access S3 images bucket"
  policy      = data.aws_iam_policy_document.lambda_s3_access.json
}

resource "aws_iam_role_policy_attachment" "lambda_s3_access" {
  role       = aws_iam_role.lambda_execution_role.name
  policy_arn = aws_iam_policy.lambda_s3_policy.arn
}

# DynamoDB access policy
data "aws_iam_policy_document" "lambda_dynamodb_access" {
  statement {
    effect = "Allow"

    actions = [
      "dynamodb:PutItem",
      "dynamodb:GetItem",
      "dynamodb:UpdateItem",
      "dynamodb:Query",
      "dynamodb:Scan",
      "dynamodb:BatchWriteItem"
    ]

    resources = [
      aws_dynamodb_table.image_analysis_results.arn,
      "${aws_dynamodb_table.image_analysis_results.arn}/index/*",
      aws_dynamodb_table.workflow_logs.arn
    ]
  }
}

resource "aws_iam_policy" "lambda_dynamodb_policy" {
  name        = "${local.project_name}-lambda-dynamodb-policy"
  description = "Allows Lambda to access DynamoDB tables"
  policy      = data.aws_iam_policy_document.lambda_dynamodb_access.json
}

resource "aws_iam_role_policy_attachment" "lambda_dynamodb_access" {
  role       = aws_iam_role.lambda_execution_role.name
  policy_arn = aws_iam_policy.lambda_dynamodb_policy.arn
}

# Rekognition access policy
data "aws_iam_policy_document" "lambda_rekognition_access" {
  statement {
    effect = "Allow"

    actions = [
      "rekognition:DetectLabels",
      "rekognition:DetectFaces",
      "rekognition:DetectText",
      "rekognition:RecognizeCelebrities",
      "rekognition:DetectModerationLabels"
    ]

    resources = ["*"]
  }
}

resource "aws_iam_policy" "lambda_rekognition_policy" {
  name        = "${local.project_name}-lambda-rekognition-policy"
  description = "Allows Lambda to use AWS Rekognition"
  policy      = data.aws_iam_policy_document.lambda_rekognition_access.json
}

resource "aws_iam_role_policy_attachment" "lambda_rekognition_access" {
  role       = aws_iam_role.lambda_execution_role.name
  policy_arn = aws_iam_policy.lambda_rekognition_policy.arn
}

# EventBridge access policy for Lambda
data "aws_iam_policy_document" "lambda_eventbridge_access" {
  statement {
    effect = "Allow"

    actions = [
      "events:PutEvents"
    ]

    resources = ["*"]
  }
}

resource "aws_iam_policy" "lambda_eventbridge_policy" {
  name        = "${local.project_name}-lambda-eventbridge-policy"
  description = "Allows Lambda to publish to EventBridge"
  policy      = data.aws_iam_policy_document.lambda_eventbridge_access.json
}

resource "aws_iam_role_policy_attachment" "lambda_eventbridge_access" {
  role       = aws_iam_role.lambda_execution_role.name
  policy_arn = aws_iam_policy.lambda_eventbridge_policy.arn
}

# CloudWatch Metrics access
data "aws_iam_policy_document" "lambda_cloudwatch_metrics" {
  statement {
    effect = "Allow"

    actions = [
      "cloudwatch:PutMetricData"
    ]

    resources = ["*"]
  }
}

resource "aws_iam_policy" "lambda_cloudwatch_metrics_policy" {
  name        = "${local.project_name}-lambda-cloudwatch-metrics"
  description = "Allows Lambda to publish CloudWatch metrics"
  policy      = data.aws_iam_policy_document.lambda_cloudwatch_metrics.json
}

resource "aws_iam_role_policy_attachment" "lambda_cloudwatch_metrics" {
  role       = aws_iam_role.lambda_execution_role.name
  policy_arn = aws_iam_policy.lambda_cloudwatch_metrics_policy.arn
}

# ===== STEP FUNCTIONS IAM ROLE =====

data "aws_iam_policy_document" "sfn_assume_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["states.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "step_functions_role" {
  name               = "${local.project_name}-stepfunctions-role"
  assume_role_policy = data.aws_iam_policy_document.sfn_assume_role.json

  tags = merge(local.common_tags, {
    Name = "Step Functions Role"
  })
}

data "aws_iam_policy_document" "sfn_lambda_invoke" {
  statement {
    effect = "Allow"

    actions = [
      "lambda:InvokeFunction"
    ]

    resources = [
      "arn:aws:lambda:${var.aws_region}:*:function:${local.project_name}-*"
    ]
  }
}

resource "aws_iam_policy" "sfn_lambda_policy" {
  name        = "${local.project_name}-sfn-lambda-policy"
  description = "Allows Step Functions to invoke Lambda"
  policy      = data.aws_iam_policy_document.sfn_lambda_invoke.json
}

resource "aws_iam_role_policy_attachment" "sfn_lambda_invoke" {
  role       = aws_iam_role.step_functions_role.name
  policy_arn = aws_iam_policy.sfn_lambda_policy.arn
}

resource "aws_iam_role_policy_attachment" "sfn_cloudwatch_logs" {
  role       = aws_iam_role.step_functions_role.name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchLogsFullAccess"
}

# ===== EVENTBRIDGE IAM ROLE =====

data "aws_iam_policy_document" "eventbridge_assume_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["events.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "eventbridge_role" {
  name               = "${local.project_name}-eventbridge-role"
  assume_role_policy = data.aws_iam_policy_document.eventbridge_assume_role.json

  tags = merge(local.common_tags, {
    Name = "EventBridge Role"
  })
}

data "aws_iam_policy_document" "eventbridge_sfn_invoke" {
  statement {
    effect = "Allow"

    actions = [
      "states:StartExecution"
    ]

    resources = [
      "arn:aws:states:${var.aws_region}:*:stateMachine:${local.project_name}-*"
    ]
  }
}

resource "aws_iam_policy" "eventbridge_sfn_policy" {
  name        = "${local.project_name}-eventbridge-sfn-policy"
  description = "Allows EventBridge to start Step Functions"
  policy      = data.aws_iam_policy_document.eventbridge_sfn_invoke.json
}

resource "aws_iam_role_policy_attachment" "eventbridge_sfn_invoke" {
  role       = aws_iam_role.eventbridge_role.name
  policy_arn = aws_iam_policy.eventbridge_sfn_policy.arn
}
