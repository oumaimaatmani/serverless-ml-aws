# =============================================================================
# TERRAFORM OUTPUTS
# Values to use after deployment
# =============================================================================

output "s3_bucket_name" {
  description = "Name of S3 bucket for images"
  value       = aws_s3_bucket.images_bucket.id
}

output "s3_bucket_arn" {
  description = "ARN of S3 bucket"
  value       = aws_s3_bucket.images_bucket.arn
}

output "s3_upload_url" {
  description = "S3 URL for uploading images"
  value       = "s3://${aws_s3_bucket.images_bucket.id}/uploads/"
}

output "project_summary" {
  description = "Project configuration summary"
  value = {
    project_name = local.project_name
    environment  = var.environment
    region       = var.aws_region
  }
}

output "useful_commands" {
  description = "Useful AWS CLI commands"
  value = {
    upload_test_image = "aws s3 cp test-image.jpg s3://${aws_s3_bucket.images_bucket.id}/uploads/"
    list_executions   = "aws stepfunctions list-executions --state-machine-arn ${aws_sfn_state_machine.image_processing_workflow.arn}"
    query_results     = "aws dynamodb scan --table-name ${aws_dynamodb_table.image_analysis_results.name}"
    view_logs         = "aws logs tail /aws/lambda/${aws_lambda_function.rekognition_analyzer.function_name} --follow"
  }
}

output "api_gateway_endpoint" {
  description = "API Gateway endpoint URL for results"
  value       = aws_apigatewayv2_stage.results_api_stage.invoke_url
}

output "results_api_docs" {
  description = "API documentation"
  value = {
    base_url = "${aws_apigatewayv2_stage.results_api_stage.invoke_url}"
    endpoints = {
      get_all = {
        method  = "GET"
        path    = "/results"
        example = "${aws_apigatewayv2_stage.results_api_stage.invoke_url}/results"
      }
      get_by_id = {
        method  = "GET"
        path    = "/results/{image_id}"
        example = "${aws_apigatewayv2_stage.results_api_stage.invoke_url}/results/test-final.jpg"
      }
      with_filters = {
        method  = "GET"
        path    = "/results?confidence=80&is_safe=true&has_faces=true&limit=50"
        example = "${aws_apigatewayv2_stage.results_api_stage.invoke_url}/results?confidence=80&is_safe=true"
      }
    }
  }
}
