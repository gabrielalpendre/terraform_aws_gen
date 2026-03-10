resource "aws_subnet" "this" {
  vpc_id                  = local.config.vpc_id
  cidr_block              = local.config.cidr_block
  availability_zone       = local.config.availability_zone
  map_public_ip_on_launch = local.config.map_public_ip_on_launch
  tags                    = local.config.tags
}