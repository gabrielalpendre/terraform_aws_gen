resource "aws_ecs_task_definition" "this" {
  family                   = local.config.family
  container_definitions    = jsonencode(local.config.container_definitions)
  requires_compatibilities = try(local.config.requires_compatibilities, ["FARGATE"])

  network_mode    = try(local.config.network_mode, "awsvpc")
  cpu             = try(local.config.cpu, null)
  memory          = try(local.config.memory, null)
  task_role_arn   = try(local.config.task_role_arn, null)
  execution_role_arn = try(local.config.execution_role_arn, null)

  tags = try(local.config.tags, {})
}