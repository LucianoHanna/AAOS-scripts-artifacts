#!/usr/bin/env bash
# ==============================================================================
# fetch_aaos.sh - Baixa os artefatos da nightly build de AAOS para Cuttlefish
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

# Configurações padrão
BRANCH="${BRANCH:-aosp-android-latest-release}"
TARGET="${TARGET:-aosp_cf_x86_64_auto-userdebug}"
BUILD_ID="${BUILD_ID:-}"

echo -e "${BLUE}====================================================${NC}"
echo -e "${BLUE}  Download de Artefatos AAOS Nightly (Cuttlefish)  ${NC}"
echo -e "${BLUE}====================================================${NC}"
echo -e "Branch:   ${YELLOW}${BRANCH}${NC}"
echo -e "Target:   ${YELLOW}${TARGET}${NC}"
if [ -n "$BUILD_ID" ]; then
    echo -e "Build ID: ${YELLOW}${BUILD_ID}${NC}"
else
    echo -e "Build ID: ${YELLOW}Última build bem-sucedida (latest nightly)${NC}"
fi
echo -e "Destino:  ${YELLOW}${TARGET_DIR}${NC}\n"

mkdir -p "$TARGET_DIR"
cd "$TARGET_DIR"

# Verifica se o utilitário 'cvd' está disponível
if command -v cvd >/dev/null 2>&1; then
    echo -e "${GREEN}Utilitário 'cvd' encontrado no sistema.${NC}"
    FETCH_CMD="cvd fetch"
else
    # Verifica se já temos cvd no binário local de host
    if [ -x "${TARGET_DIR}/bin/cvd" ]; then
        FETCH_CMD="${TARGET_DIR}/bin/cvd fetch"
    else
        echo -e "${YELLOW}'cvd' não encontrado no PATH nem em ${TARGET_DIR}/bin/cvd.${NC}"
        echo -e "${YELLOW}Tentando usar fetch_cvd ou solicitando instalação do pacote cuttlefish-base.${NC}"
        if command -v fetch_cvd >/dev/null 2>&1; then
            FETCH_CMD="fetch_cvd"
        else
            echo -e "${RED}Erro: Nem 'cvd' nem 'fetch_cvd' foram encontrados.${NC}"
            echo -e "Certifique-se de executar primeiro:"
            echo -e "  ${GREEN}sudo ./scripts/setup_host.sh${NC}"
            echo -e "para instalar os pacotes oficiais do Cuttlefish."
            exit 1
        fi
    fi
fi

echo -e "\n${GREEN}Iniciando download dos artefatos...${NC}"
echo "Isso pode levar alguns minutos dependendo da sua conexão (tamanho aprox. ~3 a 5 GB)."

if [ -n "$BUILD_ID" ]; then
    DEFAULT_BUILD_SPEC="${BRANCH}/${BUILD_ID}"
    BUILD_ARG="--default_build=${DEFAULT_BUILD_SPEC}"
    TARGET_ARG="--target=${TARGET}"
    echo "Executando: $FETCH_CMD $BUILD_ARG $TARGET_ARG --target_directory=${TARGET_DIR}"
    $FETCH_CMD "$BUILD_ARG" "$TARGET_ARG" --target_directory="${TARGET_DIR}"
else
    DEFAULT_BUILD_SPEC="${BRANCH}/${TARGET}"
    BUILD_ARG="--default_build=${DEFAULT_BUILD_SPEC}"
    echo "Executando: $FETCH_CMD $BUILD_ARG --target_directory=${TARGET_DIR}"
    $FETCH_CMD "$BUILD_ARG" --target_directory="${TARGET_DIR}"
fi

echo -e "\n${GREEN}=== Download concluído com sucesso! ===${NC}"
echo -e "Artefatos disponíveis em: ${TARGET_DIR}"
ls -lh "${TARGET_DIR}"
