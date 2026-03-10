# Gerador de Terraform a partir de Recursos AWS

Este projeto automatiza a criação de código Terraform (Infrastructure as Code) a partir de recursos já existentes na sua conta AWS. Ele inspeciona os recursos especificados, extrai suas configurações atuais e gera uma estrutura de módulos Terraform pronta para uso.

## O que o projeto faz?

O script `app.py` lê uma lista de recursos de um arquivo `resources.yaml`, conecta-se à AWS usando `boto3` para buscar os detalhes de configuração de cada um desses recursos e, em seguida, usa templates para gerar arquivos `.tf` que representam esses recursos.

O objetivo é facilitar a "engenharia reversa" de uma infraestrutura existente para o formato de código gerenciável pelo Terraform.

## Requisitos

*   **Python 3.x**
*   **Bibliotecas Python**: `boto3` e `PyYAML`. Instale-as com o comando:
    ```bash
    pip install boto3 pyyaml
    ```
*   **Credenciais da AWS**: Configure suas credenciais no ambiente onde o script será executado (ex: via variáveis de ambiente ou `~/.aws/credentials`). A role/usuário precisa de permissões de leitura (Describe/Get/List) para os serviços que deseja importar.
*   **Arquivo `resources.yaml`**: Um arquivo na raiz do projeto que lista os recursos a serem importados.
*   **Diretório `terraform_templates`**: Um diretório contendo os arquivos de template (`.tf.tpl`) para cada tipo de recurso suportado.

## Como usar

1.  **Liste os recursos**: Crie e preencha o arquivo `resources.yaml` com os identificadores dos recursos que você deseja importar. O formato varia para cada serviço.

    *Exemplo de `resources.yaml`*:
    ```yaml
    s3:
      - name: "meu-bucket-incrivel"

    lambda:
      - name: "minha-funcao-que-nao-lambe"

    load_balancer:
      - arn: "arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/app/meu-proxy-maluco/..."
    ```

2.  **Execute o script**: Rode o `app.py` a partir do seu terminal.
    ```bash
    python app.py
    ```

## O que é gerado?

Após a execução, o script cria os modulos em `terraform/` com a seguinte estrutura:

```
terraform/
├── main.tf
├── providers.tf
└── modules/
    ├── s3/
    │   └── meu_bucket_incrivel/
    │       ├── config.yaml  # Dados extraídos da AWS
    │       └── main.tf      # Lógica do Terraform para o bucket
    └── lambda/
        └── minha_funcao_que_nao_lambe/
            ├── config.yaml
            └── main.tf
    ...
```

*   **`terraform/main.tf`**: Arquivo raiz que instancia todos os módulos gerados.
*   **`terraform/modules/<tipo>/<nome>`**: Um módulo Terraform para cada recurso importado.
    *   `config.yaml`: Contém os dados brutos (configurações, tags, etc.) do recurso, extraídos da AWS.
    *   `main.tf`: Contém a lógica HCL (Terraform) que lê o `config.yaml` e declara o recurso. Este arquivo é gerado a partir do template correspondente em `terraform_templates/`.