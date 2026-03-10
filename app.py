import os
import yaml
import boto3
import logging
from botocore.exceptions import ClientError

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def gerar_dados_s3(resource_name, client):
    """
    Busca informações de um bucket S3 e retorna um dicionário com seus atributos.
    """
    bucket_name = resource_name
    logging.info(f"Buscando detalhes para o bucket S3: {bucket_name}...")
    try:

        try:
            tags_response = client.get_bucket_tagging(Bucket=bucket_name)
            tags = {tag['Key']: tag['Value'] for tag in tags_response.get('TagSet', [])}
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchTagSet' or e.response['Error']['Code'] == 'AuthorizationHeaderMalformed':
                tags = {}
            else:
                raise

        return {
            "bucket": bucket_name,
            "tags": tags
        }

    except ClientError as e:
        logging.error(f"Não foi possível encontrar ou acessar o bucket S3 '{bucket_name}': {e}")
        return None

def gerar_dados_lambda(resource_name, client):
    """
    Busca informações de uma função Lambda e retorna um dicionário com seus atributos.
    """
    function_name = resource_name
    logging.info(f"Buscando detalhes para a função Lambda: {function_name}...")
    try:
        response = client.get_function(FunctionName=function_name)
        config = response['Configuration']

        return {
            "function_name": config['FunctionName'],
            "role": config['Role'],
            "handler": config['Handler'],
            "runtime": config['Runtime'],
            "timeout": config.get('Timeout', 3),
            "memory_size": config.get('MemorySize', 128),
            "tags": response.get('Tags', {})
        }

    except ClientError as e:
        logging.error(f"Não foi possível encontrar ou acessar a função Lambda '{function_name}': {e}")
        return None

def gerar_dados_wafv2(resource_name, client):
    """
    Busca informações de uma WebACL do WAFv2. resource_name deve ser um dict com name, scope e id.
    """
    acl_name = resource_name.get('name')
    scope = resource_name.get('scope')
    acl_id = resource_name.get('id')
    logging.info(f"Buscando detalhes para a WebACL: {acl_name} (Scope: {scope})")
    try:
        response = client.get_web_acl(Name=acl_name, Scope=scope, Id=acl_id)
        web_acl = response['WebACL']
        return {
            "name": web_acl['Name'],
            "scope": web_acl['Scope'],
            "default_action": {k.lower(): v for k, v in web_acl['DefaultAction'].items()},
            "visibility_config": {
                "cloudwatch_metrics_enabled": web_acl['VisibilityConfig']['CloudWatchMetricsEnabled'],
                "metric_name": web_acl['VisibilityConfig']['MetricName'],
                "sampled_requests_enabled": web_acl['VisibilityConfig']['SampledRequestsEnabled'],
            },
            # Rules são complexas e omitidas para simplicidade inicial.
        }
    except ClientError as e:
        logging.error(f"Não foi possível encontrar ou acessar a WebACL '{acl_name}': {e}")
        return None

def gerar_dados_vpc_subnet(resource_name, client):
    """Busca informações de uma Subnet de VPC."""
    subnet_id = resource_name
    logging.info(f"Buscando detalhes para a Subnet: {subnet_id}...")
    try:
        response = client.describe_subnets(SubnetIds=[subnet_id])
        if not response.get('Subnets'):
            logging.error(f"Subnet '{subnet_id}' não encontrada.")
            return None
        subnet = response['Subnets'][0]
        return {
            "vpc_id": subnet['VpcId'],
            "cidr_block": subnet['CidrBlock'],
            "availability_zone": subnet['AvailabilityZone'],
            "map_public_ip_on_launch": subnet.get('MapPublicIpOnLaunch', False),
            "tags": {tag['Key']: tag['Value'] for tag in subnet.get('Tags', [])}
        }
    except ClientError as e:
        logging.error(f"Não foi possível encontrar ou acessar a Subnet '{subnet_id}': {e}")
        return None

def gerar_dados_load_balancer(resource_name, client):
    """Busca informações de um Load Balancer (ALB/NLB)."""
    lb_arn = resource_name
    logging.info(f"Buscando detalhes para o Load Balancer: {lb_arn}...")
    try:
        lb_response = client.describe_load_balancers(LoadBalancerArns=[lb_arn])
        if not lb_response.get('LoadBalancers'):
            logging.error(f"Load Balancer '{lb_arn}' não encontrado.")
            return None
        lb = lb_response['LoadBalancers'][0]

        tags_response = client.describe_tags(ResourceArns=[lb_arn])
        tags = {tag['Key']: tag['Value'] for tag_desc in tags_response.get('TagDescriptions', []) for tag in tag_desc.get('Tags', [])}

        return {
            "name": lb['LoadBalancerName'],
            "internal": lb.get('Scheme') == 'internal',
            "load_balancer_type": lb['Type'],
            "security_groups": lb.get('SecurityGroups', []),
            "subnets": [az['SubnetId'] for az in lb.get('AvailabilityZones', [])],
            "tags": tags
        }

    except ClientError as e:
        logging.error(f"Não foi possível encontrar ou acessar o Load Balancer '{lb_arn}': {e}")
        return None

def gerar_dados_ecs_service(resource_name, client):
    """Busca informações de um Service ECS. resource_name deve ser um dict com cluster e service."""
    cluster_name = resource_name.get('cluster')
    service_name = resource_name.get('service')
    logging.info(f"Buscando detalhes para o Service ECS: {service_name} no cluster {cluster_name}...")
    try:
        response = client.describe_services(cluster=cluster_name, services=[service_name])
        if not response.get('services'):
            logging.error(f"Service ECS '{service_name}' no cluster '{cluster_name}' não encontrado.")
            return None
        service = response['services'][0]

        # Extrai a configuração de rede, se existir
        net_config = service.get('networkConfiguration', {}).get('awsvpcConfiguration', {})

        # Extrai os load balancers
        load_balancers = [
            {
                "target_group_arn": lb.get('targetGroupArn'),
                "container_name": lb.get('containerName'),
                "container_port": lb.get('containerPort'),
            } for lb in service.get('loadBalancers', [])
        ]

        return {
            "name": service['serviceName'],
            "cluster": cluster_name,
            "task_definition": service.get('taskDefinition'),
            "desired_count": service.get('desiredCount', 1),
            "launch_type": service.get('launchType', 'FARGATE'),
            "network_configuration": {
                "subnets": net_config.get('subnets', []),
                "security_groups": net_config.get('securityGroups', []),
                "assign_public_ip": net_config.get('assignPublicIp') == 'ENABLED',
            },
            "load_balancers": load_balancers,
        }
    except ClientError as e:
        logging.error(f"Não foi possível encontrar ou acessar o Service ECS '{service_name}': {e}")
        return None

def gerar_dados_cloudfront(resource_name, client):
    """Busca informações de uma Distribuição CloudFront."""
    dist_id = resource_name
    logging.info(f"Buscando detalhes para a Distribuição CloudFront: {dist_id}...")
    try:
        response = client.get_distribution_config(Id=dist_id)
        config = response['DistributionConfig']
        return {
            "enabled": config['Enabled'],
            "comment": config.get('Comment', ''),
            "price_class": config.get('PriceClass', 'PriceClass_All'),
            "is_ipv6_enabled": config.get('IsIPV6Enabled', False),
            # Origins, behaviors, etc., são muito complexos e omitidos para simplicidade.
        }
    except ClientError as e:
        logging.error(f"Não foi possível encontrar ou acessar a Distribuição '{dist_id}': {e}")
        return None

RESOURCE_MAP = {
    's3': {
        'client': 's3',
        'generator': gerar_dados_s3,
        'template': 's3.tf.tpl'
    },
    'lambda': {
        'client': 'lambda',
        'generator': gerar_dados_lambda,
        'template': 'lambda.tf.tpl'
    },
    'wafv2': {
        'client': 'wafv2',
        'generator': gerar_dados_wafv2,
        'template': 'wafv2.tf.tpl'
    },
    'vpc_subnet': {
        'client': 'ec2',
        'generator': gerar_dados_vpc_subnet,
        'template': 'vpc_subnet.tf.tpl'
    },
    'load_balancer': {
        'client': 'elbv2',
        'generator': gerar_dados_load_balancer,
        'template': 'load_balancer.tf.tpl'
    },
    'ecs_service': {
        'client': 'ecs',
        'generator': gerar_dados_ecs_service,
        'template': 'ecs_service.tf.tpl'
    },
    'cloudfront': {
        'client': 'cloudfront',
        'generator': gerar_dados_cloudfront,
        'template': 'cloudfront.tf.tpl'
    },
}

def criar_diretorios(base_path):
    """Garante que a estrutura de diretórios para os módulos exista."""
    os.makedirs(os.path.join(base_path, 'modules'), exist_ok=True)

def main(yaml_file, output_dir):
    """Função principal que orquestra a geração do Terraform."""
    logging.info(f"Iniciando geração de Terraform a partir de '{yaml_file}'")
    criar_diretorios(output_dir)

    with open(yaml_file, 'r') as f:
        resources_to_generate = yaml.safe_load(f)

    root_main_tf_content = ""

    for resource_type, resource_list in resources_to_generate.items():
        if resource_type not in RESOURCE_MAP:
            logging.warning(f"Tipo de recurso '{resource_type}' não suportado. Pulando.")
            continue

        config = RESOURCE_MAP[resource_type]
        generator_func = config['generator']
        template_file = config['template']
        client = boto3.client(config['client'], region_name="us-east-1")

        for resource_name in resource_list:
            module_name_suffix = resource_name if isinstance(resource_name, str) else resource_name.get('name', resource_name.get('service', 'default'))
            safe_module_name = "".join(c if c.isalnum() else '_' for c in module_name_suffix)

            data_dict = generator_func(resource_name, client)

            if data_dict:
                module_path = os.path.join(output_dir, 'modules', resource_type, safe_module_name)
                os.makedirs(module_path, exist_ok=True)

                with open(os.path.join(module_path, 'config.yaml'), 'w') as yf:
                    yaml.dump(data_dict, yf, default_flow_style=False, sort_keys=False)

                template_path = os.path.join('terraform_templates', template_file)
                with open(template_path, 'r') as tpl_file:
                    hcl_template = tpl_file.read()

                module_main_tf = f"locals {{\n  config = yamldecode(file(\"${{path.module}}/config.yaml\"))\n}}\n\n{hcl_template}"
                with open(os.path.join(module_path, 'main.tf'), 'w') as mtf:
                    mtf.write(module_main_tf)
                
                logging.info(f"Módulo '{safe_module_name}' gerado em: {module_path}")

                root_main_tf_content += f'\nmodule "{resource_type}_{safe_module_name}" {{\n  source = "./modules/{resource_type}/{safe_module_name}"\n}}\n'

    main_tf_path = os.path.join(output_dir, 'main.tf')
    with open(main_tf_path, 'w') as f:
        f.write("# Arquivo gerado automaticamente.\n" + root_main_tf_content)

    logging.info("Geração de código concluída!")
    logging.info(f"O arquivo '{main_tf_path}' foi populado com sucesso.")

if __name__ == '__main__':
    INPUT_YAML = 'resources.yaml'
    OUTPUT_DIR = 'terraform'
    
    if not os.path.exists(INPUT_YAML):
        logging.error(f"Arquivo de entrada '{INPUT_YAML}' não encontrado. Crie-o com a lista de recursos.")
    else:
        main(INPUT_YAML, OUTPUT_DIR)