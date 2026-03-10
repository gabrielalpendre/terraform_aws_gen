resource "aws_api_gateway_rest_api" "this" {
  name        = local.config.name
  description = try(local.config.description, null)
  body        = jsonencode(local.config.body)

  endpoint_configuration {
    types = local.config.endpoint_configuration.types
  }

  tags = try(local.config.tags, {})
}