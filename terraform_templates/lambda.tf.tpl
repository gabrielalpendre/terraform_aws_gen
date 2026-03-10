# Atenção: O código-fonte (filename/s3_bucket) precisa ser fornecido manualmente.
resource "aws_lambda_function" "this" {
  function_name = local.config.function_name
  role          = local.config.role
  handler       = local.config.handler
  runtime       = local.config.runtime
  timeout       = local.config.timeout
  memory_size   = local.config.memory_size
  tags          = local.config.tags
}