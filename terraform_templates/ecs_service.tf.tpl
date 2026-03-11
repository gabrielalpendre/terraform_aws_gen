resource "aws_ecs_service" "this" {
  name            = local.config.name
  cluster         = local.config.cluster
  task_definition = local.config.task_definition
  desired_count   = local.config.desired_count
  launch_type     = local.config.launch_type

  deployment_maximum_percent         = local.config.deployment_maximum_percent
  deployment_minimum_healthy_percent = local.config.deployment_minimum_healthy_percent

  scheduling_strategy = local.config.scheduling_strategy

  dynamic "deployment_configuration" {
    for_each = local.config.deployment_configuration != null ? [local.config.deployment_configuration] : []
    content {
      # Estes argumentos são válidos apenas para a estratégia ROLLING_UPDATE.
      # Para a estratégia CANARY, este bloco é necessário.
      # O Terraform ignora se o bloco interno estiver vazio.
      dynamic "canary_configuration" {
        for_each = lookup(deployment_configuration.value, "canary_configuration", null) != null ? [deployment_configuration.value.canary_configuration] : []
        content {
          canary_percent              = canary_configuration.value.canary_percent
          canary_bake_time_in_minutes = canary_configuration.value.canary_bake_time_in_minutes
        }
      }
    }
  }

  dynamic "deployment_controller" {
    for_each = local.config.deployment_controller != null && length(keys(local.config.deployment_controller)) > 0 ? [local.config.deployment_controller] : []
    content {
      type = lookup(deployment_controller.value, "type", null)
    }
  }

  dynamic "load_balancer" {
    for_each = local.config.load_balancers
    content {
      target_group_arn = load_balancer.value.target_group_arn
      container_name   = load_balancer.value.container_name
      container_port   = load_balancer.value.container_port

      dynamic "advanced_configuration" {
        for_each = lookup(load_balancer.value, "advanced_configuration", null) != null ? [load_balancer.value.advanced_configuration] : []
        content {
          alternate_target_group_arn = advanced_configuration.value.alternate_target_group_arn
          production_listener_rule   = advanced_configuration.value.production_listener_rule_arn
          role_arn                   = advanced_configuration.value.role_arn
        }
      }
    }
  }

  network_configuration {
    subnets          = local.config.network_configuration.subnets
    security_groups  = local.config.network_configuration.security_groups
    assign_public_ip = local.config.network_configuration.assign_public_ip
  }

  tags = local.config.tags
}