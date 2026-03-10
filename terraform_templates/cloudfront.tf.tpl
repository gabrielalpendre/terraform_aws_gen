# Atenção: Configuração de Origins, Default Cache Behavior e outras são complexas
# e precisam ser adicionadas manualmente.
resource "aws_cloudfront_distribution" "this" {
  enabled         = local.config.enabled
  is_ipv6_enabled = local.config.is_ipv6_enabled
  comment         = local.config.comment
  price_class     = local.config.price_class

  # Exemplo de como adicionar origins e behaviors (requer dados no YAML)
  # dynamic "origin" {
  #   for_each = local.config.origins
  #   content {
  #     domain_name = origin.value.domain_name
  #     origin_id   = origin.value.origin_id
  #   }
  # }

  # default_cache_behavior {
  #   ...
  # }

  # restrictions {
  #   geo_restriction {
  #     restriction_type = "none"
  #   }
  # }

  # viewer_certificate {
  #   cloudfront_default_certificate = true
  # }
}