s3:
  - bucket1
  - bucket2
lambda:
  - lambda1

wafv2:
  - name: "my-web-acl-name"
    scope: "REGIONAL"
    id: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"

ecs_service:
  - cluster: "my-ecs-cluster"
    service: "my-ecs-service-name"

vpc_subnet:
  - "subnet-0123456789abcdef0"

load_balancer:
  - "arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/app/my-load-balancer/50dc6c495c0c9188"

cloudfront:
  - "E1234567890ABC"