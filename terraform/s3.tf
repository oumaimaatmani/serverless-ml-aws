# =============================================================================
# S3 BUCKET CONFIGURATION
# Creates S3 bucket for storing uploaded images
# =============================================================================

# Main S3 bucket for images
resource "aws_s3_bucket" "images_bucket" {
  bucket = "${local.project_name}-images-${random_id.bucket_suffix.hex}"

  tags = merge(local.common_tags, {
    Name        = "Images Bucket"
    Description = "Store uploaded images for ML processing"
  })
}

# Enable versioning for traceability
resource "aws_s3_bucket_versioning" "images_bucket" {
  bucket = aws_s3_bucket.images_bucket.id

  versioning_configuration {
    status = "Enabled"
  }
}

# CORS configuration for browser uploads
resource "aws_s3_bucket_cors_configuration" "images_bucket" {
  bucket = aws_s3_bucket.images_bucket.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "PUT", "POST", "DELETE", "HEAD"]
    allowed_origins = ["*"]
    expose_headers  = ["ETag", "x-amz-server-side-encryption", "x-amz-request-id"]
    max_age_seconds = 3000
  }
}

# Block public access for security
resource "aws_s3_bucket_public_access_block" "images_bucket" {
  bucket = aws_s3_bucket.images_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Enable EventBridge notifications
resource "aws_s3_bucket_notification" "images_bucket" {
  bucket      = aws_s3_bucket.images_bucket.id
  eventbridge = true
}

# Encryption at rest
resource "aws_s3_bucket_server_side_encryption_configuration" "images_bucket" {
  bucket = aws_s3_bucket.images_bucket.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Lifecycle rule to archive old images (optional)
resource "aws_s3_bucket_lifecycle_configuration" "images_bucket" {
  bucket = aws_s3_bucket.images_bucket.id

  rule {
    id     = "expire-objects"
    status = "Enabled"

    filter {
      prefix = "uploads/"
    }

    expiration {
      days = 365
    }
  }
}