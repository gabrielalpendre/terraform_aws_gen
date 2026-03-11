resource "aws_wafv2_web_acl" "from_import" {
  name        = local.config.name
  description = local.config.description
  scope       = local.config.scope

  default_action {
    dynamic "allow" {
      for_each = lookup(local.config.default_action, "allow", null) != null ? [local.config.default_action.allow] : []
      content {}
    }
    dynamic "block" {
      for_each = lookup(local.config.default_action, "block", null) != null ? [local.config.default_action.block] : []
      content {}
    }
  }

  dynamic "custom_response_body" {
    for_each = local.config.custom_response_bodies
    content {
      key          = custom_response_body.key
      content_type = custom_response_body.value.content_type
      content      = custom_response_body.value.content
    }
  }

  dynamic "rule" {
    for_each = { for r in local.config.rules : r.name => r }
    content {
      name     = rule.value.name
      priority = rule.value.priority

      dynamic "action" {
        for_each = lookup(rule.value, "action", null) != null ? [rule.value.action] : []
        content {
          dynamic "allow" {
            for_each = lookup(action.value, "allow", null) != null ? [action.value.allow] : []
            content {}
          }
          dynamic "block" {
            for_each = lookup(action.value, "block", null) != null ? [action.value.block] : []
            content {
              dynamic "custom_response" {
                for_each = lookup(block.value, "custom_response", null) != null ? [block.value.custom_response] : []
                content {
                  response_code            = custom_response.value.response_code
                  custom_response_body_key = lookup(custom_response.value, "custom_response_body_key", null)
                }
              }
            }
          }
          dynamic "count" {
            for_each = lookup(action.value, "count", null) != null ? [action.value.count] : []
            content {}
          }
          dynamic "captcha" {
            for_each = lookup(action.value, "captcha", null) != null ? [action.value.captcha] : []
            content {}
          }
        }
      }

      dynamic "override_action" {
        for_each = lookup(rule.value, "override_action", null) != null ? [rule.value.override_action] : []
        content {
          dynamic "count" {
            for_each = lookup(override_action.value, "count", null) != null ? [override_action.value.count] : []
            content {}
          }
          dynamic "none" {
            for_each = lookup(override_action.value, "none", null) != null ? [override_action.value.none] : []
            content {}
          }
        }
      }

      statement {
        # Bloco dinâmico para os statement mais comuns. 
        # Como o statement é recursivo e complexo, suportamos os níveis principais.
        
        dynamic "managed_rule_group_statement" {
          for_each = lookup(rule.value.statement, "managed_rule_group_statement", null) != null ? [rule.value.statement.managed_rule_group_statement] : []
          content {
            name        = managed_rule_group_statement.value.name
            vendor_name = managed_rule_group_statement.value.vendor_name
            
            dynamic "rule_action_override" {
              for_each = lookup(managed_rule_group_statement.value, "rule_action_overrides", [])
              content {
                 name = rule_action_override.value.name
                 action_to_use {
                   dynamic "count" {
                     for_each = lookup(rule_action_override.value.action_to_use, "count", null) != null ? [1] : []
                     content {}
                   }
                   dynamic "allow" {
                     for_each = lookup(rule_action_override.value.action_to_use, "allow", null) != null ? [1] : []
                     content {}
                   }
                   dynamic "block" {
                     for_each = lookup(rule_action_override.value.action_to_use, "block", null) != null ? [1] : []
                     content {}
                   }
                 }
              }
            }
          }
        }

        dynamic "ip_set_reference_statement" {
          for_each = lookup(rule.value.statement, "ip_set_reference_statement", null) != null ? [rule.value.statement.ip_set_reference_statement] : []
          content {
            arn = ip_set_reference_statement.value.arn
          }
        }

        dynamic "rate_based_statement" {
          for_each = lookup(rule.value.statement, "rate_based_statement", null) != null ? [rule.value.statement.rate_based_statement] : []
          content {
            limit              = rate_based_statement.value.limit
            aggregate_key_type = lookup(rate_based_statement.value, "aggregate_key_type", "IP")
          }
        }
        
        # ... Adicionar outros statements conforme necessário ...
      }

      visibility_config {
        cloudwatch_metrics_enabled = lookup(rule.value.visibility_config, "cloudwatch_metrics_enabled", true)
        metric_name                = rule.value.visibility_config.metric_name
        sampled_requests_enabled   = lookup(rule.value.visibility_config, "sampled_requests_enabled", true)
      }
    }
  }

  visibility_config {
    cloudwatch_metrics_enabled = local.config.visibility_config.cloudwatch_metrics_enabled
    metric_name                = local.config.visibility_config.metric_name
    sampled_requests_enabled   = local.config.visibility_config.sampled_requests_enabled
  }

  tags = local.config.tags
}