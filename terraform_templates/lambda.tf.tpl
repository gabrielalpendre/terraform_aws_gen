resource "aws_lambda_function" "this" {
  # O código da função (ex: s3_bucket, s3_key) é omitido intencionalmente
  # para focar na restauração da configuração "stateless".
  # Você precisará gerenciar o artefato de deploy separadamente.
  function_name = local.config.function_name
  role          = local.config.role
  handler       = local.config.handler
  runtime       = local.config.runtime
  description   = try(local.config.description, null)
  architectures = try(local.config.architectures, ["x86_64"])
  timeout       = try(local.config.timeout, 3)
  memory_size   = try(local.config.memory_size, 128)

  dynamic "environment" {
    for_each = length(keys(try(local.config.environment_variables, {}))) > 0 ? [1] : []
    content {
      variables = local.config.environment_variables
    }
  }

  # A configuração de VPC será anexada se definida
  vpc_config {
    subnet_ids         = try(local.config.vpc_config.subnet_ids, [])
    security_group_ids = try(local.config.vpc_config.security_group_ids, [])
  }

  tags = try(local.config.tags, {})
}