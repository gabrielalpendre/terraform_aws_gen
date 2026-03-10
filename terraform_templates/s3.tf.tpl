resource "aws_s3_bucket" "this" {
  bucket = local.config.bucket
  tags   = try(local.config.tags, {})
}

resource "aws_s3_bucket_versioning" "this" {
  bucket = aws_s3_bucket.this.id
  versioning_configuration {
    status = local.config.versioning_status
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "this" {
  count  = try(local.config.server_side_encryption_configuration, null) != null ? 1 : 0
  bucket = aws_s3_bucket.this.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = local.config.server_side_encryption_configuration.rules[0].apply_server_side_encryption_by_default.sse_algorithm
      kms_master_key_id = try(local.config.server_side_encryption_configuration.rules[0].apply_server_side_encryption_by_default.kms_master_key_id, null)
    }
  }
}

resource "aws_s3_bucket_policy" "this" {
  count  = try(local.config.policy, null) != null ? 1 : 0
  bucket = aws_s3_bucket.this.id
  policy = jsonencode(local.config.policy)
}