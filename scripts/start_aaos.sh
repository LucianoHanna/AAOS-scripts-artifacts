#!/usr/bin/env bash
# ==============================================================================
# start_aaos.sh - Inicia o Android Automotive OS no Cuttlefish
# ==============================================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TARGET_DIR="${PROJECT_ROOT}/artifacts"

echo -e "${BLUE}====================================================${NC}"
echo -e "${BLUE}       Iniciando Android Automotive OS (Cuttlefish) ${NC}"
echo -e "${BLUE}====================================================${NC}"

# 1. Verifica permissões de KVM
if [ ! -r /dev/kvm ] || [ ! -w /dev/kvm ]; then
    echo -e "${RED}Erro: Permissão negada para acessar /dev/kvm.${NC}"
    echo -e "Certifique-se de que seu usuário pertence ao grupo 'kvm'."
    echo -e "Tente rodar no terminal:"
    echo -e "  ${GREEN}newgrp kvm${NC}"
    echo -e "e execute este script novamente nesta mesma janela de terminal."
    exit 1
fi

# 2. Verifica se os artefatos foram baixados
if [ ! -d "$TARGET_DIR" ]; then
    echo -e "${RED}Erro: Diretório de artefatos '$TARGET_DIR' não encontrado.${NC}"
    echo -e "Execute primeiro: ${GREEN}./scripts/fetch_aaos.sh${NC}"
    exit 1
fi

cd "$TARGET_DIR"

# 3. Configurações de display automotivo (painel central widescreen)
# Resolução típica para infotainment automotivo: 1920x1080 @ 213/240 DPI
WIDTH="${DISPLAY_WIDTH:-1920}"
HEIGHT="${DISPLAY_HEIGHT:-1080}"
DPI="${DISPLAY_DPI:-213}"
CPUS="${NUM_CPUS:-4}"
RAM_MB="${MEMORY_MB:-6144}"

echo -e "Configurações da VM:"
echo -e "  Display:     ${YELLOW}${WIDTH}x${HEIGHT} @ ${DPI} DPI${NC}"
echo -e "  vCPUs:       ${YELLOW}${CPUS}${NC}"
echo -e "  Memória RAM: ${YELLOW}${RAM_MB} MB${NC}"
echo -e "  WebRTC:      ${YELLOW}https://localhost:8443${NC}\n"

# 4. Inicia Cuttlefish
if command -v cvd >/dev/null 2>&1; then
    if cvd fleet 2>/dev/null | grep -q "INSTANCE"; then
        echo -e "${GREEN}Iniciando instância existente via 'cvd start'...${NC}"
        cvd start
    else
        echo -e "${GREEN}Criando e iniciando nova instância via 'cvd create'...${NC}"
        cvd create \
            --host_path="$TARGET_DIR" \
            --product_path="$TARGET_DIR" \
            --cpus="$CPUS" \
            --memory_mb="$RAM_MB" \
            --display="width=${WIDTH},height=${HEIGHT},dpi=${DPI}"
    fi
elif [ -x "./bin/launch_cvd" ]; then
    echo -e "${GREEN}Iniciando via './bin/launch_cvd'...${NC}"
    HOME="$TARGET_DIR" ./bin/launch_cvd \
        -daemon \
        -cpus="$CPUS" \
        -memory_mb="$RAM_MB" \
        -display0="width=${WIDTH},height=${HEIGHT},dpi=${DPI}" \
        -start_webrtc=true
else
    echo -e "${RED}Erro: Não foi encontrado o comando 'cvd' nem o executável './bin/launch_cvd'.${NC}"
    echo -e "Execute primeiro: ${GREEN}./scripts/fetch_aaos.sh${NC}"
    exit 1
fi

echo -e "\n${GREEN}=== Cuttlefish iniciado em background! ===${NC}"
echo -e "\nPara visualizar e interagir com o Android Automotive:"
echo -e "  1. Abra seu navegador em: ${BLUE}https://localhost:8443${NC}"
echo -e "     (Ignore o aviso de certificado autoassinado SSL no navegador)"
echo -e "\nPara verificar o status do dispositivo via ADB:"
echo -e "  ${YELLOW}adb devices${NC}"
echo -e "  ${YELLOW}adb shell getprop sys.boot_completed${NC}"
echo -e "\nPara acompanhar os logs de boot:"
echo -e "  ${YELLOW}tail -f ${TARGET_DIR}/cuttlefish_runtime/launcher.log${NC}"
echo -e "\nPara parar o Cuttlefish:"
echo -e "  ${YELLOW}./scripts/stop_aaos.sh${NC}"
