resource "aws_ecs_service" "this" {
  name            = local.config.name
  cluster         = local.config.cluster
  task_definition = local.config.task_definition
  desired_count   = local.config.desired_count
  launch_type     = local.config.launch_type

  scheduling_strategy = try(local.config.scheduling_strategy, "REPLICA")

  dynamic "deployment_configuration" {
    for_each = try(local.config.deployment_configuration, null) != null ? [1] : []
    content {
      maximum_percent        = try(local.config.deployment_configuration.maximum_percent, 200)
      minimum_healthy_percent = try(local.config.deployment_configuration.minimum_healthy_percent, 100)
    }
  }

  dynamic "network_configuration" {
    for_each = local.config.launch_type == "FARGATE" ? [1] : []
    content {
      subnets          = local.config.network_configuration.subnets
      security_groups  = try(local.config.network_configuration.security_groups, [])
      assign_public_ip = try(local.config.network_configuration.assign_public_ip, false)
    }
  }

  dynamic "load_balancer" {
    for_each = try(local.config.load_balancers, [])
    content {
      target_group_arn = load_balancer.value.target_group_arn
      container_name   = load_balancer.value.container_name
      container_port   = load_balancer.value.container_port
    }
  }

  dynamic "service_registries" {
    for_each = try(local.config.service_registries, [])
    content {
      registry_arn   = service_registries.value.registry_arn
      port           = try(service_registries.value.port, null)
      container_port = try(service_registries.value.container_port, null)
      container_name = try(service_registries.value.container_name, null)
    }
  }

  health_check_grace_period_seconds = try(local.config.health_check_grace_period_seconds, null)
  enable_ecs_managed_tags           = try(local.config.enable_ecs_managed_tags, false)
  enable_execute_command            = try(local.config.enable_execute_command, false)
  propagate_tags                    = try(local.config.propagate_tags, null)

  tags = try(local.config.tags, {})
}