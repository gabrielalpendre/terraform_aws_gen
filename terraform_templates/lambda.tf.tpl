resource "aws_lambda_function" "this" {
  function_name = local.config.function_name
  description   = try(local.config.description, null)
  role          = local.config.role
  handler       = local.config.package_type == "Zip" ? local.config.handler : null
  runtime       = local.config.package_type == "Zip" ? local.config.runtime : null
  architectures = try(local.config.architectures, ["x86_64"])

  timeout     = try(local.config.timeout, 3)
  memory_size = try(local.config.memory_size, 128)

  # Lógica para a fonte do código
  # Define apenas os argumentos relevantes para o tipo de pacote.
  package_type = local.config.package_type

  # Para funções baseadas em imagem
  image_uri = local.config.package_type == "Image" ? local.config.image_uri : null

  # Para funções baseadas em Zip (requer preenchimento manual do bucket/key no config.yaml)
  s3_bucket        = local.config.package_type == "Zip" ? try(local.config.s3_bucket, null) : null
  s3_key           = local.config.package_type == "Zip" ? try(local.config.s3_key, null) : null
  s3_object_version = local.config.package_type == "Zip" ? try(local.config.s3_object_version, null) : null
  source_code_hash = local.config.package_type == "Zip" ? try(local.config.source_code_hash, null) : null

  dynamic "environment" {
    for_each = length(keys(try(local.config.environment_variables, {}))) > 0 ? [1] : []
    content {
      variables = local.config.environment_variables
    }
  }

  dynamic "vpc_config" {
    for_each = try(local.config.vpc_config.vpc_id, null) != null ? [1] : []
    content {
      subnet_ids         = local.config.vpc_config.subnet_ids
      security_group_ids = local.config.vpc_config.security_group_ids
    }
  }

  layers = try(local.config.layers, [])

  dynamic "file_system_config" {
    for_each = try(local.config.filesystem_configs, [])
    content {
      arn              = file_system_config.value.arn
      local_mount_path = file_system_config.value.local_mount_path
    }
  }

  tags = try(local.config.tags, {})
}