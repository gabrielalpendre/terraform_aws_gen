resource "aws_ecs_task_definition" "this" {
  family                = local.config.family
  container_definitions = jsonencode(local.config.container_definitions)

  # Opcionais
  cpu                      = try(local.config.cpu, null)
  memory                   = try(local.config.memory, null)
  network_mode             = try(local.config.network_mode, "awsvpc")
  task_role_arn            = try(local.config.task_role_arn, null)
  execution_role_arn       = try(local.config.execution_role_arn, null)
  requires_compatibilities = try(local.config.requires_compatibilities, ["FARGATE"])

  dynamic "volume" {
    for_each = try(local.config.volumes, [])
    content {
      name = volume.value.name
      dynamic "host_path" {
        for_each = try(volume.value.host_path, null) != null ? [1] : []
        content {
          path = volume.value.host_path
        }
      }
      # Adicionar outros tipos de volume (efs, fsx) aqui se necessário
    }
  }

  tags = try(local.config.tags, {})
}