resource "aws_lb" "this" {
  name               = local.config.name
  internal           = local.config.internal
  load_balancer_type = local.config.load_balancer_type
  security_groups    = local.config.security_groups
  subnets            = local.config.subnets
  tags               = local.config.tags
}