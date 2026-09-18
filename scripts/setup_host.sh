#!/usr/bin/env bash
# ==============================================================================
# setup_host.sh - Prepara o host Ubuntu para rodar Android Cuttlefish
# ==============================================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== 1. Verificando privilégios de administrador ===${NC}"
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Erro: Este script precisa ser executado com sudo ou como root.${NC}"
    echo "Uso: sudo $0"
    exit 1
fi

TARGET_USER="${SUDO_USER:-$USER}"
echo -e "Configurando para o usuário: ${YELLOW}${TARGET_USER}${NC}"

echo -e "\n${GREEN}=== 2. Verificando suporte a virtualização de hardware (KVM) ===${NC}"
if grep -E -q "(vmx|svm)" /proc/cpuinfo; then
    echo -e "Suporte a KVM detectado na CPU (${GREEN}OK${NC})."
else
    echo -e "${RED}Aviso: Virtualização de hardware (VT-x ou AMD-V) não detectada em /proc/cpuinfo!${NC}"
    echo "Verifique se a virtualização está habilitada na BIOS/UEFI."
fi

if [ -e /dev/kvm ]; then
    echo -e "Dispositivo /dev/kvm presente (${GREEN}OK${NC})."
else
    echo -e "${YELLOW}Dispositivo /dev/kvm não encontrado. Carregando módulo kvm...${NC}"
    modprobe kvm || true
    modprobe kvm_amd || modprobe kvm_intel || true
fi

echo -e "\n${GREEN}=== 3. Configurando repositório oficial do Cuttlefish (Google Artifact Registry) ===${NC}"
apt-get update
apt-get install -y curl ca-certificates gnupg

KEY_PATH="/etc/apt/trusted.gpg.d/artifact-registry.asc"
echo "Baixando chave GPG do repositório..."
curl -fsSL https://us-apt.pkg.dev/doc/repo-signing-key.gpg -o "$KEY_PATH"
chmod a+r "$KEY_PATH"

LIST_PATH="/etc/apt/sources.list.d/artifact-registry.list"
REPO_LINE="deb https://us-apt.pkg.dev/projects/android-cuttlefish-artifacts android-cuttlefish main"

if [ -f "$LIST_PATH" ] && grep -Fxq "$REPO_LINE" "$LIST_PATH"; then
    echo "Repositório já configurado em $LIST_PATH."
else
    echo "$REPO_LINE" > "$LIST_PATH"
    echo "Repositório adicionado a $LIST_PATH."
fi

echo -e "\n${GREEN}=== 4. Atualizando lista de pacotes e instalando Cuttlefish Host Tools ===${NC}"
apt-get update

# Instala dependências e pacotes oficiais do Cuttlefish
apt-get install -y \
    cuttlefish-base \
    cuttlefish-user \
    adb \
    curl \
    jq \
    tar \
    unzip \
    bridge-utils \
    iptables

echo -e "\n${GREEN}=== 5. Configurando permissões de usuário e grupos ===${NC}"
for grp in kvm cvdnetwork render virtaccess; do
    if ! getent group "$grp" > /dev/null; then
        echo "Criando grupo $grp..."
        groupadd -f "$grp"
    fi
    echo "Adicionando $TARGET_USER ao grupo $grp..."
    usermod -aG "$grp" "$TARGET_USER"
done

# Assegura que /dev/kvm tenha permissões de leitura e escrita para o grupo kvm
if [ -e /dev/kvm ]; then
    chown root:kvm /dev/kvm
    chmod 0660 /dev/kvm
fi

echo -e "\n${GREEN}=== 6. Configurando firewall para pontes de rede do Cuttlefish (Docker/UFW fix) ===${NC}"
# Docker e UFW colocam a política de FORWARD como DROP por padrão, bloqueando o VHAL e DHCP do Cuttlefish.
iptables -I FORWARD -i cvd-ebr -j ACCEPT 2>/dev/null || true
iptables -I FORWARD -o cvd-ebr -j ACCEPT 2>/dev/null || true
iptables -I FORWARD -i cvd-wbr -j ACCEPT 2>/dev/null || true
iptables -I FORWARD -o cvd-wbr -j ACCEPT 2>/dev/null || true

# Se o Docker estiver rodando, libera também na chain DOCKER-USER
if iptables -L DOCKER-USER -n >/dev/null 2>&1; then
    iptables -I DOCKER-USER -i cvd-ebr -j ACCEPT 2>/dev/null || true
    iptables -I DOCKER-USER -o cvd-ebr -j ACCEPT 2>/dev/null || true
    iptables -I DOCKER-USER -i cvd-wbr -j ACCEPT 2>/dev/null || true
    iptables -I DOCKER-USER -o cvd-wbr -j ACCEPT 2>/dev/null || true
fi

echo -e "\n${GREEN}=== Configuração concluída com sucesso! ===${NC}"
echo -e "O usuário ${YELLOW}${TARGET_USER}${NC} foi adicionado aos grupos necessários."
echo -e "${YELLOW}IMPORTANTE:${NC} Para aplicar as permissões dos novos grupos nesta sessão sem reiniciar:"
echo -e "  Execute no seu terminal: ${GREEN}newgrp kvm${NC}"
echo -e "Ou faça logoff e login novamente (ou reinicie o computador para aplicar todas as regras de rede udev do cuttlefish)."
