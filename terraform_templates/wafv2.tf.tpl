resource "aws_wafv2_web_acl" "this" {
  name        = local.config.name
  description = try(local.config.description, null)
  scope       = local.config.scope

  default_action {
    dynamic "allow" {
      for_each = try(local.config.default_action.allow, null) != null ? [local.config.default_action.allow] : []
      content {
        dynamic "custom_request_handling" {
          for_each = try(allow.value.custom_request_handling, null) != null ? [allow.value.custom_request_handling] : []
          content {
            insert_header {
              name  = custom_request_handling.value.insert_header.name
              value = custom_request_handling.value.insert_header.value
            }
          }
        }
      }
    }
    dynamic "block" {
      for_each = try(local.config.default_action.block, null) != null ? [local.config.default_action.block] : []
      content {
        dynamic "custom_response" {
          for_each = try(block.value.custom_response, null) != null ? [block.value.custom_response] : []
          content {
            response_code = custom_response.value.response_code
          }
        }
      }
    }
  }

  visibility_config {
    cloudwatch_metrics_enabled = local.config.visibility_config.cloudwatch_metrics_enabled
    metric_name                = local.config.visibility_config.metric_name
    sampled_requests_enabled   = local.config.visibility_config.sampled_requests_enabled
  }

  # As regras (rules) são complexas e geralmente gerenciadas separadamente.
  # Adicionar a lógica de `dynamic "rule"` aqui se a estrutura de `local.config.rules` for estável.

  tags = try(local.config.tags, {})
}