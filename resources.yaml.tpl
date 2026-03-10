# Exemplo de arquivo de recursos. Use o formato chave: valor para cada item.
s3:
  - name: "meu-bucket-exemplo-1"
  - name: "meu-bucket-exemplo-2"

lambda:
  - name: "minha-funcao-lambda-exemplo"

wafv2:
  - name: "my-web-acl-name"
    scope: "REGIONAL"
    id: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"

vpc_subnet:
  - id: "subnet-0123456789abcdef0"

load_balancer:
  - arn: "arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/app/my-load-balancer/50dc6c495c0c9188"

ecs_task_definition:
  - name: "minha-task-definition-familia"

ecs_service:
  - cluster: "my-ecs-cluster"
    service: "my-ecs-service-name"

cloudfront:
  - id: "E1234567890ABC"

api_gateway:
  - name: "Minha-API-Exemplo"

kms:
  - alias: "alias/minha-chave-kms" # Pode ser alias, key_id ou arn

sns:
  - arn: "arn:aws:sns:us-east-1:123456789012:meu-topico-sns"