#!/bin/bash

# Script para aplicar ou planejar um recurso específico do Terraform.
set -e

show_help() {
    echo "Uso: $0 [flags] [ação]"
    echo ""
    echo "Ações:"
    echo "  plan      (padrão) Executa um 'terraform plan' no módulo alvo."
    echo "  apply     Executa um 'terraform apply' no módulo alvo."
    echo "  destroy   Executa um 'terraform destroy' no módulo alvo."
    echo ""
    echo "Flags:"
    echo "  -ls, --list-modules    Lista os nomes dos módulos definidos em 'main.tf'."
    echo "  -m, --module <nome>    Especifica o nome do módulo alvo a ser usado no comando."
    echo "  -h, --help             Mostra esta mensagem de ajuda."
    echo "  -a, --auto-approve     Aplica as mudanças sem confirmação interativa (para apply/destroy)."
    echo "  -sv, --skip-validate   Pula a etapa de validação do Terraform."
    echo ""
    echo "Exemplos:"
    echo "  $0 -ls"
    echo "  $0 --module s3:meu-bucket-incrivel plan"
    echo "  $0 -m lambda:minha-funcao apply"
}

list_modules() {
    local main_tf_path="main.tf"
    if [ ! -f "$main_tf_path" ]; then
        echo "Erro: Arquivo '$main_tf_path' não encontrado. Execute o app.py primeiro."
        exit 1
    fi
    echo "Módulos disponíveis em '$main_tf_path':"
    grep -oP 'module "\K[^"]+' "$main_tf_path" | sed 's/^/  /'
}

if [ $# -eq 0 ]; then
    show_help
    exit 0
fi

TARGET_INPUT=""
ACTION=""
AUTO_APPROVE_FLAG=""
SKIP_VALIDATE=false

while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
        -h|--help)
        show_help
        exit 0
        ;;
        -ls|--list-modules)
        list_modules
        exit 0
        ;;
        -m|--module)
        TARGET_INPUT="$2"
        shift
        shift
        ;;
        -a|--auto-approve)
        AUTO_APPROVE_FLAG="-auto-approve"
        shift
        ;;
        -sv|--skip-validate)
        SKIP_VALIDATE=true
        shift
        ;;
        plan|apply|destroy)
        ACTION="$1"
        shift
        ;;
        *)
        echo "Erro: Argumento desconhecido '$1'"
        show_help
        exit 1
        ;;
    esac
done

if [ -z "$ACTION" ]; then
    ACTION="plan"
fi

if [ -z "$TARGET_INPUT" ]; then
    echo "Erro: Nenhum nome de módulo alvo especificado. Use a flag -m ou --module."
    show_help
    exit 1
fi

# --- Lógica Principal ---
if [ ! -d "modules" ] || [ -z "$(ls -A modules)" ]; then
    echo "Erro: Diretório 'modules' não encontrado ou está vazio. Execute o app.py primeiro."
    exit 1
fi
KNOWN_TYPES=$(ls modules | awk '{ print length, $0 }' | sort -nr | cut -d' ' -f2-)
RESOURCE_TYPE=""

for type in $KNOWN_TYPES; do
    if [[ "$TARGET_INPUT" == "${type}_"* ]]; then
        RESOURCE_TYPE=$type
        break
    fi
done

if [ -z "$RESOURCE_TYPE" ]; then
    echo "Erro: Não foi possível determinar o tipo de recurso para o módulo '$TARGET_INPUT'."
    exit 1
fi

TEMPLATE_PATH="../terraform_templates/${RESOURCE_TYPE}.tf.tpl"
if [ ! -f "$TEMPLATE_PATH" ]; then
    echo "Erro: Arquivo de template não encontrado em '$TEMPLATE_PATH'."
    exit 1
fi

RESOURCE_LINE=$(grep -m 1 -oP 'resource\s+"[^"]+"\s+"[^"]+"' "$TEMPLATE_PATH")
if [ -z "$RESOURCE_LINE" ]; then
    echo "Erro: Não foi possível encontrar uma definição de 'resource' no template '$TEMPLATE_PATH'."
    exit 1
fi

INTERNAL_ADDRESS=$(echo "$RESOURCE_LINE" | awk -F'"' '{print $2 "." $4}')
MODULE_TARGET="module.${TARGET_INPUT}.${INTERNAL_ADDRESS}"

if [ "$SKIP_VALIDATE" = false ]; then
    echo "--> Validando a configuração geral do Terraform..."
    if ! terraform validate -no-color; then
        echo "------------------------------------------------------------------------"
        echo "ERRO: O Terraform precisa validar toda a configuração antes de aplicar um alvo específico."
        exit 1
    fi
else
    echo "--> Etapa de validação pulada (--skip-validate)."
fi

FINAL_COMMAND="terraform $ACTION -target=\"$MODULE_TARGET\""

if [[ ("$ACTION" == "apply" || "$ACTION" == "destroy") && -n "$AUTO_APPROVE_FLAG" ]]; then
    FINAL_COMMAND="$FINAL_COMMAND $AUTO_APPROVE_FLAG"
fi

echo "--> Executando o comando:"
echo "    $FINAL_COMMAND"
eval "$FINAL_COMMAND"