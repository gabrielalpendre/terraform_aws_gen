resource "aws_kms_key" "this" {
  description             = try(local.config.description, null)
  key_usage               = try(local.config.key_usage, "ENCRYPT_DECRYPT")
  policy                  = jsonencode(local.config.policy)
  is_enabled              = try(local.config.is_enabled, true)
  # deletion_window_in_days não pode ser importado diretamente, então um valor padrão é usado.
  deletion_window_in_days = 10

  tags = try(local.config.tags, {})
}