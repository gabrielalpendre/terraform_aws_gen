import os
import yaml
import boto3
import logging
from botocore.exceptions import ClientError

import requests # Adicionado para baixar o código da função
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def gerar_dados_s3(resource_name, client):
    """
    Busca informações de um bucket S3. resource_name deve ser um dict com a chave 'name'.
    """
    bucket_name = resource_name['name']
    logging.info(f"Buscando detalhes para o bucket S3: {bucket_name}...")
    try:
        tags = {}
        try:
            tags_response = client.get_bucket_tagging(Bucket=bucket_name)
            tags = {tag['Key']: tag['Value'] for tag in tags_response.get('TagSet', [])}
        except ClientError as e:
            if e.response['Error']['Code'] not in ['NoSuchTagSet', 'AuthorizationHeaderMalformed']:
                logging.warning(f"Não foi possível obter tags para o bucket {bucket_name}: {e}")

        versioning = client.get_bucket_versioning(Bucket=bucket_name).get('Status', 'Disabled')

        try:
            encryption = client.get_bucket_encryption(Bucket=bucket_name)['ServerSideEncryptionConfiguration']
        except ClientError as e:
            if e.response['Error']['Code'] == 'ServerSideEncryptionConfigurationNotFoundError':
                encryption = None
            else:
                logging.warning(f"Não foi possível obter configuração de criptografia para {bucket_name}: {e}")
                encryption = None

        try:
            policy_str = client.get_bucket_policy(Bucket=bucket_name).get('Policy')
            policy = yaml.safe_load(policy_str) if policy_str else None
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchBucketPolicy':
                policy = None
            else:
                logging.warning(f"Não foi possível obter política do bucket {bucket_name}: {e}")
                policy = None

        return {
            "bucket": bucket_name,
            "versioning_status": versioning,
            "server_side_encryption_configuration": _processar_regras_recursivamente(encryption),
            "policy": policy,
            "tags": tags
        }

    except ClientError as e:
        logging.error(f"Não foi possível encontrar ou acessar o bucket S3 '{bucket_name}': {e}")
        return None

def gerar_dados_lambda(resource_name, client, module_path):
    """
    Busca informações de uma função Lambda. resource_name deve ser um dict com a chave 'name'.
    """
    function_name = resource_name['name']
    logging.info(f"Buscando detalhes para a função Lambda: {function_name}...")
    try:
        response = client.get_function(FunctionName=function_name)
        config = response['Configuration']
        code_info = response.get('Code', {})
        env_vars = config.get('Environment', {}).get('Variables', {})
        layers = [layer['Arn'] for layer in config.get('Layers', [])]

        filesystem_configs = [{ 'arn': fsc['Arn'], 'local_mount_path': fsc['LocalMountPath'] } for fsc in config.get('FileSystemConfigs', [])]

        package_type = config.get('PackageType')
        filename = None

        if package_type == 'Zip':
            # A API não fornece o bucket/key de origem, então baixamos o código.
            code_location = response.get('Code', {}).get('Location')
            if code_location:
                try:
                    logging.info(f"Baixando código da função '{function_name}'...")
                    zip_content = requests.get(code_location).content
                    filename = f"{function_name}_source.zip"
                    with open(os.path.join(module_path, filename), 'wb') as f:
                        f.write(zip_content)
                except requests.RequestException as e:
                    logging.error(f"Falha ao baixar o código da função '{function_name}': {e}")
                    filename = None

        return {
            "function_name": config['FunctionName'],
            "description": config.get('Description', ''),
            "role": config['Role'],
            "handler": config.get('Handler') if package_type == 'Zip' else None,
            "runtime": config.get('Runtime') if package_type == 'Zip' else None,
            "architectures": config.get('Architectures', ['x86_64']),
            "timeout": config.get('Timeout', 3),
            "memory_size": config.get('MemorySize', 128),
            "package_type": package_type,
            "image_uri": code_info.get('ImageUri') if package_type == 'Image' else None, # Correctly fetch from code_info
            "filename": filename, # Caminho para o arquivo .zip baixado
            "environment_variables": env_vars,
            "dead_letter_config": config.get('DeadLetterConfig', {}),
            "kms_key_arn": config.get('KMSKeyArn', ''),
            "tracing_config": config.get('TracingConfig', {}),
            "layers": layers,
            "filesystem_configs": filesystem_configs,
            "vpc_config": config.get('VpcConfig', {}),
            "tags": response.get('Tags', {})
        }

    except ClientError as e:
        logging.error(f"Não foi possível encontrar ou acessar a função Lambda '{function_name}': {e}")
        return None

def _processar_regras_recursivamente(obj):
    """Converte recursivamente as chaves de um objeto de PascalCase para snake_case."""
    if isinstance(obj, dict):
        new_dict = {}
        for k, v in obj.items():
            new_key = ''.join(['_' + c.lower() if c.isupper() else c for c in k]).lstrip('_')
            new_dict[new_key] = _processar_regras_recursivamente(v)
        return new_dict
    elif isinstance(obj, list):
        return [_processar_regras_recursivamente(elem) for elem in obj]
    else:
        return obj

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
        tags_response = client.list_tags_for_resource(ResourceARN=web_acl['ARN'])
        tags = {tag['Key']: tag['Value'] for tag in tags_response.get('TagInfo', {}).get('TagList', [])}

        return {
            "name": web_acl['Name'],
            "description": web_acl.get('Description', ''),
            "scope": scope,
            "default_action": _processar_regras_recursivamente(web_acl['DefaultAction']),
            "visibility_config": {
                "cloudwatch_metrics_enabled": web_acl['VisibilityConfig']['CloudWatchMetricsEnabled'],
                "metric_name": web_acl['VisibilityConfig']['MetricName'],
                "sampled_requests_enabled": web_acl['VisibilityConfig']['SampledRequestsEnabled'],
            },
            "custom_response_bodies": _processar_regras_recursivamente(web_acl.get('CustomResponseBodies', {})),
            "rules": _processar_regras_recursivamente(web_acl.get('Rules', [])),
            "tags": tags,
        }
    except ClientError as e:
        if e.response['Error']['Code'] == 'WAFNonexistentItemException':
            logging.error(f"A WebACL '{acl_name}' com ID '{acl_id}' e escopo '{scope}' não foi encontrada.")
            return None

        logging.error(f"Não foi possível encontrar ou acessar a WebACL '{acl_name}': {e}")
        return None

def gerar_dados_vpc_subnet(resource_name, client):
    """Busca informações de uma Subnet de VPC. resource_name deve ser um dict com a chave 'id'."""
    subnet_id = resource_name['id']
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
    """Busca informações de um Load Balancer (ALB/NLB). resource_name deve ser um dict com a chave 'arn'."""
    lb_arn = resource_name['arn']
    logging.info(f"Buscando detalhes para o Load Balancer: {lb_arn}...")
    try:
        lb_response = client.describe_load_balancers(LoadBalancerArns=[lb_arn])
        if not lb_response.get('LoadBalancers'):
            logging.error(f"Load Balancer '{lb_arn}' não encontrado.")
            return None
        lb = lb_response['LoadBalancers'][0]

        tags_response = client.describe_tags(ResourceArns=[lb_arn])
        tags = {}
        if tags_response.get('TagDescriptions'):
            tags = {tag['Key']: tag['Value'] for tag in tags_response['TagDescriptions'][0].get('Tags', [])}

        attributes_response = client.describe_load_balancer_attributes(LoadBalancerArn=lb_arn)
        attributes = {attr['Key'].replace('.', '_'): attr['Value'] for attr in attributes_response.get('Attributes', [])}

        return {
            "name": lb['LoadBalancerName'],
            "internal": lb.get('Scheme') == 'internal',
            "load_balancer_type": lb['Type'],
            "attributes": attributes,
            "security_groups": lb.get('SecurityGroups', []),
            "subnets": [az['SubnetId'] for az in lb.get('AvailabilityZones', [])],
            "tags": tags
        }

    except ClientError as e:
        logging.error(f"Não foi possível encontrar ou acessar o Load Balancer '{lb_arn}': {e}")
        return None

def gerar_dados_ecs_task_definition(resource_name, client):
    """Busca informações de uma Task Definition do ECS. resource_name deve ser um dict com a chave 'name'."""
    task_def_name = resource_name['name']
    logging.info(f"Buscando detalhes para a Task Definition: {task_def_name}...")
    try:
        response = client.describe_task_definition(taskDefinition=task_def_name)
        task_def = response['taskDefinition']

        return {
            "family": task_def['family'],
            "container_definitions": _processar_regras_recursivamente(task_def.get('containerDefinitions', [])),
            "cpu": task_def.get('cpu'),
            "memory": task_def.get('memory'),
            "network_mode": task_def.get('networkMode'),
            "task_role_arn": task_def.get('taskRoleArn'),
            "execution_role_arn": task_def.get('executionRoleArn'),
            "requires_compatibilities": task_def.get('requiresCompatibilities', []),
            "volumes": _processar_regras_recursivamente(task_def.get('volumes', [])),
            "placement_constraints": _processar_regras_recursivamente(task_def.get('placementConstraints', [])), # Note: 'key' and 'value' for tags are lowercase in boto3 response
            "proxy_configuration": _processar_regras_recursivamente(task_def.get('proxyConfiguration')),
            "tags": {tag['key']: tag['value'] for tag in task_def.get('tags', [])}
        }

    except ClientError as e:
        logging.error(f"Não foi possível encontrar ou acessar a Task Definition '{task_def_name}': {e}", exc_info=True)
        return None

def gerar_dados_ecs_service(resource_name, client):
    """Busca informações de um Service ECS. resource_name deve ser um dict com cluster e service."""
    cluster_name = resource_name.get('cluster')
    service_name = resource_name.get('service')
    logging.info(f"Buscando detalhes para o Service ECS: {service_name} no cluster {cluster_name}...")
    try:
        response = client.describe_services(cluster=cluster_name, services=[service_name], include=['TAGS'])
        if not response.get('services'):
            logging.error(f"Service ECS '{service_name}' no cluster '{cluster_name}' não encontrado.")
            return None
        service = response['services'][0]

        deployment_controller = service.get('deploymentController', {})
        net_config = service.get('networkConfiguration', {}).get('awsvpcConfiguration', {})

        load_balancers = [
            {
                "target_group_arn": lb.get('targetGroupArn'),
                "container_name": lb.get('containerName'),
                "container_port": lb.get('containerPort'),
            } for lb in service.get('loadBalancers', [])
        ]

        return {
            "name": service['serviceName'],
            "cluster": cluster_name, # O ARN completo do cluster é retornado, o que é ideal.
            "task_definition": service.get('taskDefinition'),
            "scheduling_strategy": service.get('schedulingStrategy', 'REPLICA'),
            "deployment_configuration": _processar_regras_recursivamente(service.get('deploymentConfiguration')),
            "desired_count": service.get('desiredCount', 1),
            "launch_type": service.get('launchType', 'FARGATE'),
            "network_configuration": {
                "subnets": net_config.get('subnets', []), # 'subnets' é com 's' no final
                "security_groups": net_config.get('securityGroups', []),
                "assign_public_ip": net_config.get('assignPublicIp') == 'ENABLED',
            },
            "load_balancers": load_balancers,
            "deployment_controller": _processar_regras_recursivamente(deployment_controller),
            "service_registries": _processar_regras_recursivamente(service.get('serviceRegistries', [])),
            "health_check_grace_period_seconds": service.get('healthCheckGracePeriodSeconds'),
            "enable_ecs_managed_tags": service.get('enableECSManagedTags', False),
            "enable_execute_command": service.get('enableExecuteCommand', False),
            "propagate_tags": service.get('propagateTags'),
            "tags": {tag['key']: tag['value'] for tag in service.get('tags', [])}
        }
    except ClientError as e:
        logging.error(f"Não foi possível encontrar ou acessar o Service ECS '{service_name}': {e}")
        return None

def gerar_dados_cloudfront(resource_name, client):
    """Busca informações de uma Distribuição CloudFront. resource_name deve ser um dict com a chave 'id'."""
    dist_id = resource_name['id']
    logging.info(f"Buscando detalhes para a Distribuição CloudFront: {dist_id}...")
    try:
        response = client.get_distribution_config(Id=dist_id)
        config = response['DistributionConfig']
        tags_response = client.list_tags_for_resource(ResourceARN=response['Distribution']['ARN'])
        tags = {tag['Key']: tag['Value'] for tag in tags_response.get('Tags', {}).get('Items', [])}

        return {
            "id": dist_id,
            "enabled": config['Enabled'],
            "comment": config.get('Comment', ''),
            "price_class": config.get('PriceClass', 'PriceClass_All'), # Ex: PriceClass_100
            "is_ipv6_enabled": config.get('IsIPV6Enabled', False),
            "aliases": _processar_regras_recursivamente(config.get('Aliases', {}).get('Items', [])),
            "default_root_object": config.get('DefaultRootObject', ''),
            "origins": _processar_regras_recursivamente(config.get('Origins', {}).get('Items', [])), # 'origins' é com 's'
            "default_cache_behavior": _processar_regras_recursivamente(config.get('DefaultCacheBehavior', {})),
            "ordered_cache_behavior": _processar_regras_recursivamente(config.get('CacheBehaviors', {}).get('Items', [])),
            "custom_error_responses": _processar_regras_recursivamente(config.get('CustomErrorResponses', {}).get('Items', [])),
            "viewer_certificate": _processar_regras_recursivamente(config.get('ViewerCertificate', {})),
            "restrictions": _processar_regras_recursivamente(config.get('Restrictions', {})),
            "web_acl_id": config.get('WebACLId', ''),
            "tags": tags,
        }
    except ClientError as e:
        logging.error(f"Não foi possível encontrar ou acessar a Distribuição '{dist_id}': {e}")
        return None

def gerar_dados_api_gateway(resource_name, client):
    """Busca informações de uma REST API do API Gateway. resource_name deve ser um dict com a chave 'name'."""
    api_name = resource_name['name']
    logging.info(f"Buscando detalhes para a API Gateway REST API: {api_name}...")
    try:
        apis = client.get_rest_apis()
        api_item = next((item for item in apis['items'] if item['name'] == api_name), None)
        if not api_item:
            logging.error(f"API Gateway com nome '{api_name}' não encontrada.")
            return None
        api_id = api_item['id']

        export = client.get_export(
            restApiId=api_id,
            stageName='prod',
            exportType='oas30',
            parameters={'extensions': 'integrations,authorizers'}
        )
        api_definition = yaml.safe_load(export['body'])

        return {
            "name": api_item['name'],
            "description": api_item.get('description', ''),
            "endpoint_configuration": _processar_regras_recursivamente(api_item.get('endpointConfiguration', {})),
            "tags": api_item.get('tags', {}),
            "body": api_definition
        }
    except ClientError as e:
        logging.error(f"Não foi possível encontrar ou acessar a API Gateway '{api_name}': {e}")
        return None

def gerar_dados_kms_key(resource_name, client):
    """Busca informações de uma chave KMS. resource_name deve ser um dict com a chave 'alias', 'id' ou 'arn'."""
    key_id_or_alias = resource_name.get('alias') or resource_name.get('id') or resource_name.get('arn')
    logging.info(f"Buscando detalhes para a chave KMS: {key_id_or_alias}...")
    try:
        response = client.describe_key(KeyId=key_id_or_alias)
        key_metadata = response['KeyMetadata']
        key_id = key_metadata['KeyId']
 
        policy_response = client.get_key_policy(KeyId=key_metadata['KeyId'], PolicyName='default')
        policy = yaml.safe_load(policy_response['Policy'])
 
        tags_response = client.list_resource_tags(KeyId=key_metadata['KeyId'])
        tags = {tag['TagKey']: tag['TagValue'] for tag in tags_response.get('Tags', [])}
 
        # O Terraform espera 'deletion_window_in_days', não um timestamp.
        # Se a chave não estiver pendente de exclusão, este campo não deve ser definido.
        deletion_window = None
 
        return {
            "description": key_metadata.get('Description', ''),
            "key_usage": key_metadata.get('KeyUsage'),
            "policy": policy, # A política é um objeto JSON, o que é correto.
            "deletion_window_in_days": deletion_window,
            "is_enabled": key_metadata.get('Enabled'),
            "tags": tags,
        }
    except ClientError as e:
        logging.error(f"Não foi possível encontrar ou acessar a chave KMS '{key_id_or_alias}': {e}")
        return None

def gerar_dados_sns_topic(resource_name, client):
    """Busca informações de um tópico SNS. resource_name deve ser um dict com a chave 'arn'."""
    topic_arn = resource_name['arn']
    logging.info(f"Buscando detalhes para o Tópico SNS: {topic_arn}...")
    try:
        attributes = client.get_topic_attributes(TopicArn=topic_arn)['Attributes']
        tags_response = client.list_tags_for_resource(ResourceARN=topic_arn)
        tags = {tag['Key']: tag['Value'] for tag in tags_response.get('Tags', [])}
        return {
            "name": attributes['DisplayName'],
            "policy": yaml.safe_load(attributes['Policy']),
            "tags": tags,
        }
    except ClientError as e:
        logging.error(f"Não foi possível encontrar ou acessar o Tópico SNS '{topic_arn}': {e}")
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
    'ecs_task_definition': {
        'client': 'ecs',
        'generator': gerar_dados_ecs_task_definition,
        'template': 'ecs_task_definition.tf.tpl'
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
    'api_gateway': {
        'client': 'apigateway',
        'generator': gerar_dados_api_gateway,
        'template': 'api_gateway.tf.tpl'
    },
    'kms': {
        'client': 'kms',
        'generator': gerar_dados_kms_key,
        'template': 'kms.tf.tpl'
    },
    'sns': {
        'client': 'sns',
        'generator': gerar_dados_sns_topic,
        'template': 'sns.tf.tpl'
    },
}


def main(yaml_file, output_dir):
    """Função principal que orquestra a geração do Terraform."""
    logging.info(f"Iniciando geração de Terraform a partir de '{yaml_file}'")

    with open(yaml_file, 'r') as f:
        resources_to_generate = yaml.safe_load(f)

    main_tf_path = os.path.join(output_dir, 'main.tf')
    new_module_blocks = []
    existing_main_tf_content = ""

    if os.path.exists(main_tf_path):
        with open(main_tf_path, 'r') as f:
            existing_main_tf_content = f.read()

    boto_clients = {}

    for resource_type, resource_list in resources_to_generate.items():
        if resource_type not in RESOURCE_MAP:
            logging.warning(f"Tipo de recurso '{resource_type}' não suportado. Pulando.")
            continue

        config = RESOURCE_MAP[resource_type]
        generator_func = config['generator']
        template_file = config['template']
        client_name = config['client']

        if client_name not in boto_clients:
            boto_clients[client_name] = boto3.client(client_name, region_name="us-east-1")
        client = boto_clients[client_name]

        for resource_item in resource_list:
            name_keys = ['name', 'service', 'id', 'arn', 'alias']
            module_name_suffix = 'default'
            for key in name_keys:
                if key in resource_item:
                    module_name_suffix = resource_item[key].split('/')[-1] # Pega a última parte de ARNs/aliases
                    break

            safe_module_name = "".join(c if c.isalnum() else '_' for c in module_name_suffix)
            module_path = os.path.join(output_dir, 'modules', resource_type, safe_module_name)
            os.makedirs(module_path, exist_ok=True)

            # Passa o module_path para o gerador, caso ele precise salvar arquivos (ex: Lambda zip)
            data_dict = generator_func(resource_item, client, module_path=module_path) if resource_type == 'lambda' else generator_func(resource_item, client)

            if data_dict:
                with open(os.path.join(module_path, 'config.yaml'), 'w') as yf:
                    yaml.dump(data_dict, yf, default_flow_style=False, sort_keys=False)

                template_path = os.path.join('terraform_templates', template_file)
                with open(template_path, 'r') as tpl_file:
                    hcl_template = tpl_file.read()

                module_main_tf = f"locals {{\n  config = yamldecode(file(\"${{path.module}}/config.yaml\"))\n}}\n\n{hcl_template}"
                with open(os.path.join(module_path, 'main.tf'), 'w') as mtf:
                    mtf.write(module_main_tf)
                
                logging.info(f"Módulo '{safe_module_name}' gerado em: {module_path}")

                module_declaration_name = f'module "{resource_type}_{safe_module_name}"'
                if module_declaration_name in existing_main_tf_content:
                    logging.info(f"Declaração para o módulo '{resource_type}_{safe_module_name}' já existe em '{main_tf_path}'. Pulando.")
                else:
                    module_block = f'\nmodule "{resource_type}_{safe_module_name}" {{\n  source = "./modules/{resource_type}/{safe_module_name}"\n}}\n'
                    new_module_blocks.append(module_block)

    if new_module_blocks:
        with open(main_tf_path, 'a') as f:
            if not existing_main_tf_content:
                f.write("# Arquivo raiz do Terraform. Módulos podem ser adicionados aqui.\n")
            f.writelines(new_module_blocks)
        logging.info(f"{len(new_module_blocks)} novo(s) módulo(s) foram adicionados ao arquivo '{main_tf_path}'.")
    else:
        logging.info("Nenhum novo módulo para adicionar ao 'main.tf'.")

if __name__ == '__main__':
    INPUT_YAML = 'resources.yaml'
    OUTPUT_DIR = 'terraform'
    # pip install requests
    
    if not os.path.exists(INPUT_YAML):
        logging.error(f"Arquivo de entrada '{INPUT_YAML}' não encontrado. Crie-o com a lista de recursos.")
    else:
        main(INPUT_YAML, OUTPUT_DIR)