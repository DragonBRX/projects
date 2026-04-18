#!/bin/bash
# =============================================================================
# EMU-GPU Toolkit - Limpeza da v1.0
# Remove arquivos antigos da versao CLI (v1.0)
# =============================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${BOLD}${CYAN}EMU-GPU Toolkit - Limpeza v1.0${NC}"
echo ""

INSTALL_DIR="$HOME/.emu-gpu"
BIN_DIR="$HOME/.local/bin"
APPS_DIR="$HOME/.local/share/applications"

# Lista de arquivos/pastas antigas da v1.0 para remover
ANTIGOS=(
    "$INSTALL_DIR/wrappers"
    "$INSTALL_DIR/scripts/cpu-governor-game.sh"
    "$INSTALL_DIR/scripts/cpu-governor-powersave.sh"
    "$INSTALL_DIR/scripts/cpu-affinity-launcher.sh"
    "$INSTALL_DIR/scripts/fps-limiter.sh"
    "$INSTALL_DIR/scripts/install-dxvk.sh"
    "$INSTALL_DIR/venv"
    "$INSTALL_DIR/activate"
    "$INSTALL_DIR/deactivate"
    "$INSTALL_DIR/icon.png"
    "$INSTALL_DIR/src"
)

REMOVIDOS=0

for item in "${ANTIGOS[@]}"; do
    if [ -e "$item" ]; then
        rm -rf "$item"
        echo -e "  ${GREEN}Removido:${NC} $item"
        REMOVIDOS=$((REMOVIDOS + 1))
    fi
done

# Remover atalho antigo do menu (v1.0)
if [ -f "$APPS_DIR/emu-gpu.desktop" ]; then
    # Verificar se eh o antigo (sem 'Toolkit' no nome)
    if ! grep -q "EMU-GPU Toolkit" "$APPS_DIR/emu-gpu.desktop" 2>/dev/null; then
        rm "$APPS_DIR/emu-gpu.desktop"
        echo -e "  ${GREEN}Removido:${NC} Atalho antigo do menu"
        REMOVIDOS=$((REMOVIDOS + 1))
    fi
fi

# Remover aliases antigos do .bashrc
if grep -q "EMU_GPU_TOOLKIT" "$HOME/.bashrc" 2>/dev/null; then
    echo -e "  ${YELLOW}Removendo aliases antigos do .bashrc...${NC}"
    # Remove bloco antigo
    sed -i '/# === EMU-GPU TOOLKIT ===/,/# ========================/d' "$HOME/.bashrc"
    REMOVIDOS=$((REMOVIDOS + 1))
fi

# Atualizar cache de apps
update-desktop-database "$APPS_DIR" 2>/dev/null || true

echo ""
if [ $REMOVIDOS -gt 0 ]; then
    echo -e "${GREEN}$REMOVIDOS itens da v1.0 removidos com sucesso!${NC}"
else
    echo -e "${YELLOW}Nenhum arquivo antigo encontrado. Ja esta limpo!${NC}"
fi
echo ""
echo -e "A v2.0 GUI esta instalada em: ${CYAN}$INSTALL_DIR/app/${NC}"
