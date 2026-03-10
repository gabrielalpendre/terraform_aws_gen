resource "aws_sns_topic" "this" {
  name   = local.config.name
  policy = jsonencode(local.config.policy)

  tags = try(local.config.tags, {})
}