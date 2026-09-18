#!/usr/bin/env bash
# ==============================================================================
# stop_aaos.sh - Encerra a instância do Android Automotive no Cuttlefish
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

echo -e "${BLUE}Encerrando instâncias do Cuttlefish...${NC}"

if command -v cvd >/dev/null 2>&1; then
    cvd stop || true
fi

if [ -d "$TARGET_DIR" ] && [ -x "${TARGET_DIR}/bin/stop_cvd" ]; then
    (cd "$TARGET_DIR" && HOME="$TARGET_DIR" ./bin/stop_cvd) || true
fi

echo -e "${GREEN}Cuttlefish finalizado.${NC}"
