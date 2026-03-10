resource "aws_lb" "this" {
  name               = local.config.name
  internal           = local.config.internal
  load_balancer_type = local.config.load_balancer_type
  security_groups    = try(local.config.security_groups, [])
  subnets            = local.config.subnets

  # Aplica os atributos dinamicamente
  for_each = try(local.config.attributes, {})
  dynamic "access_logs" {
    for_each = each.key == "access_logs.s3.enabled" && each.value == "true" ? [1] : []
    content {
      bucket  = local.config.attributes["access_logs.s3.bucket"]
      prefix  = try(local.config.attributes["access_logs.s3.prefix"], null)
      enabled = true
    }
  }

  tags = try(local.config.tags, {})
}