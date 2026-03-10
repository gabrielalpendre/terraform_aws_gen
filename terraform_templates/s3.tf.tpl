resource "aws_s3_bucket" "this" {
  bucket = local.config.bucket
  tags   = local.config.tags
}