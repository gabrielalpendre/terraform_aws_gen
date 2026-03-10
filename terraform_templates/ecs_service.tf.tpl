resource "aws_ecs_service" "this" {
  name            = local.config.name
  cluster         = local.config.cluster
  task_definition = local.config.task_definition
  desired_count   = local.config.desired_count
  launch_type     = local.config.launch_type

  dynamic "network_configuration" {
    for_each = local.config.network_configuration.subnets != [] ? [1] : []
    content {
      subnets          = local.config.network_configuration.subnets
      security_groups  = local.config.network_configuration.security_groups
      assign_public_ip = local.config.network_configuration.assign_public_ip
    }
  }

  dynamic "load_balancer" {
    for_each = local.config.load_balancers
    content {
      target_group_arn = load_balancer.value.target_group_arn
      container_name   = load_balancer.value.container_name
      container_port   = load_balancer.value.container_port
    }
  }
}