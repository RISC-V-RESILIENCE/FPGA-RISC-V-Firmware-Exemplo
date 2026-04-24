#!/bin/bash
#
# Pre-commit hook para atualizar automaticamente o histórico de arquivos markdown
# Integrado com o markdown_history_manager.py
# Versão generalizada para submódulos e repositórios principais
#

# Função para encontrar o script do gerenciador
find_manager_script() {
    local current_dir="$1"
    local repo_root="$2"
    
    # Tenta encontrar o script na pasta scripts do repositório atual
    local local_script="$repo_root/scripts/markdown_history_manager.py"
    if [ -f "$local_script" ]; then
        echo "$local_script"
        return 0
    fi
    
    # Tenta encontrar o script no diretório pai (útil para submódulos)
    local parent_repo="$(dirname "$repo_root")"
    local parent_script="$parent_repo/scripts/markdown_history_manager.py"
    if [ -f "$parent_script" ]; then
        echo "$parent_script"
        return 0
    fi
    
    # Tenta encontrar usando caminho relativo ao hook
    local hook_script="$(dirname "$0")/../../scripts/markdown_history_manager.py"
    if [ -f "$hook_script" ]; then
        echo "$hook_script"
        return 0
    fi
    
    # Se não encontrar, retorna vazio
    echo ""
    return 1
}

# Obtém diretórios
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Encontra o script do gerenciador
MANAGER_SCRIPT=$(find_manager_script "$SCRIPT_DIR" "$REPO_ROOT")

# Verifica se o script existe
if [ -z "$MANAGER_SCRIPT" ] || [ ! -f "$MANAGER_SCRIPT" ]; then
    echo "Aviso: markdown_history_manager.py não encontrado"
    echo "  Diretório do hook: $SCRIPT_DIR"
    echo "  Raiz do repositório: $REPO_ROOT"
    exit 0
fi

# Verifica se Python está disponível
if ! command -v python3 &> /dev/null; then
    echo "Aviso: python3 não encontrado, pulando atualização de histórico"
    exit 0
fi

# Obtém arquivos markdown sendo commitados
MARKDOWN_FILES=$(git diff --cached --name-only --diff-filter=ACM | grep '\.md$')

if [ -z "$MARKDOWN_FILES" ]; then
    # Nenhum arquivo markdown para processar
    exit 0
fi

# Obtém mensagem do commit (se disponível)
COMMIT_MSG=""
if [ -f ".git/COMMIT_EDITMSG" ]; then
    COMMIT_MSG=$(cat ".git/COMMIT_EDITMSG" | head -n1)
fi

# Exporta mensagem do commit para o script Python
export GIT_COMMIT_MESSAGE="$COMMIT_MSG"

# Processa cada arquivo markdown
echo "Atualizando histórico de arquivos markdown..."
echo "  Script: $MANAGER_SCRIPT"
echo "  Repositório: $REPO_ROOT"
FAILED_FILES=""

for file in $MARKDOWN_FILES; do
    if [ -f "$file" ]; then
        echo "Processando: $file"
        
        # Executa o script Python para o arquivo com parâmetros opcionais
        if python3 "$MANAGER_SCRIPT" --repo-root "$REPO_ROOT" "$file" 2>/dev/null; then
            # Adiciona o arquivo modificado novamente ao staging
            git add "$file"
            echo "✓ Histórico atualizado: $file"
        else
            echo "✗ Falha ao atualizar histórico: $file"
            FAILED_FILES="$FAILED_FILES $file"
        fi
    fi
done

# Se houver falhas, avisa mas não bloqueia o commit
if [ ! -z "$FAILED_FILES" ]; then
    echo ""
    echo "Aviso: Alguns arquivos não puderam ser atualizados:$FAILED_FILES"
    echo "O commit continuará, mas verifique os arquivos manualmente."
fi

echo "Histórico de markdown atualizado."
exit 0
