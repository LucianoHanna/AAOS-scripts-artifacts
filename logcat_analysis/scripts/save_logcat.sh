#!/usr/bin/env bash
# ==============================================================================
# save_logcat.sh - Salva o logcat completo do AAOS em arquivo .log
# ==============================================================================
# Descrição:
#   Identifica a instância ativa do Cuttlefish (AAOS) ou dispositivo ADB conectado
#   e salva o histórico completo de logs em um arquivo .log com timestamp.
#   Também atualiza o link simbólico 'aaos_logcat_latest.log' para fácil acesso.
#
# Uso:
#   ./logcat_analysis/scripts/save_logcat.sh
# ==============================================================================

set -euo pipefail

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    cat << 'EOF'
Uso: ./save_logcat.sh [OPÇÕES]

Coleta e persiste os logs completos do Android Automotive OS (Cuttlefish).

Opções:
  -h, --help    Exibe esta mensagem de ajuda.

Comportamento:
  1. Tenta obter o caminho persistido do host Cuttlefish (/var/tmp/cvd/.../logs/logcat).
  2. Caso o arquivo do host não seja acessível, extrai via 'adb logcat -b all -d'.
  3. Salva em: logcat_analysis/logs/aaos_logcat_<TIMESTAMP>.log
  4. Atualiza o link simbólico: logcat_analysis/logs/aaos_logcat_latest.log
EOF
    exit 0
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
LOGS_DIR="${ROOT_DIR}/logs"

mkdir -p "$LOGS_DIR"

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
TARGET_FILE="${LOGS_DIR}/aaos_logcat_${TIMESTAMP}.log"
LATEST_SYMLINK="${LOGS_DIR}/aaos_logcat_latest.log"

echo "=== Coletando Logcat do AAOS ==="

CVD_LOGCAT=""

# 1. Tenta identificar a instância Cuttlefish ativa via cvd fleet e jq (sem dependência de python)
if command -v cvd >/dev/null 2>&1 && command -v jq >/dev/null 2>&1; then
    RUNNING_DIR=$(cvd fleet 2>/dev/null | jq -r '.groups[]?.instances[]? | select(.status == "Running") | .instance_dir' 2>/dev/null | head -n 1 || true)
    if [ -n "$RUNNING_DIR" ] && [ -f "${RUNNING_DIR}/logs/logcat" ]; then
        CVD_LOGCAT="${RUNNING_DIR}/logs/logcat"
    fi
fi

# 2. Fallback: se cvd/jq não retornar, busca o arquivo logcat modificado mais recentemente em /var/tmp/cvd
if [ -z "$CVD_LOGCAT" ] && [ -d "/var/tmp/cvd" ]; then
    RECENT_LOGCAT=$(find /var/tmp/cvd/ -type f -name "logcat" -printf '%T@ %p\n' 2>/dev/null | sort -nr | head -n 1 | awk '{print $2}' || true)
    if [ -n "$RECENT_LOGCAT" ] && [ -f "$RECENT_LOGCAT" ]; then
        CVD_LOGCAT="$RECENT_LOGCAT"
    fi
fi

# 3. Executa a cópia do log persistente ou extrai via adb
if [ -n "$CVD_LOGCAT" ] && [ -s "$CVD_LOGCAT" ]; then
    echo "Fonte identificada (Host Cuttlefish Logcat persistente): $CVD_LOGCAT"
    echo "Copiando histórico gravado desde o boot..."
    cp "$CVD_LOGCAT" "$TARGET_FILE"
elif command -v adb >/dev/null 2>&1; then
    echo "Host logcat não acessível. Extraindo diretamente via 'adb logcat -b all -d -v threadtime'..."
    adb logcat -b all -d -v threadtime > "$TARGET_FILE"
else
    echo "Erro: Não foi possível localizar o logcat do Cuttlefish nem executar o adb." >&2
    exit 1
fi

# 4. Atualiza o link simbólico relativo para o arquivo mais recente
(cd "$LOGS_DIR" && ln -sf "$(basename "$TARGET_FILE")" "aaos_logcat_latest.log")

LINES=$(wc -l < "$TARGET_FILE")
SIZE=$(ls -lh "$TARGET_FILE" | awk '{print $5}')

echo -e "\n=== Coleta Concluída ==="
echo "  Arquivo gerado:      $TARGET_FILE"
echo "  Tamanho:             $SIZE"
echo "  Total de linhas:     $LINES"
echo "  Link simbólico:      $LATEST_SYMLINK"
