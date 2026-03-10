# Atenção: Regras, associações e logging não são gerados automaticamente.
resource "aws_wafv2_web_acl" "this" {
  name  = local.config.name
  scope = local.config.scope

  default_action {
    dynamic "allow" {
      for_each = local.config.default_action.allow != null ? [1] : []
      content {}
    }
    dynamic "block" {
      for_each = local.config.default_action.block != null ? [1] : []
      content {}
    }
  }

  visibility_config {
    cloudwatch_metrics_enabled = local.config.visibility_config.cloudwatch_metrics_enabled
    metric_name                = local.config.visibility_config.metric_name
    sampled_requests_enabled   = local.config.visibility_config.sampled_requests_enabled
  }
}