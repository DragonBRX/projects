#!/bin/bash
# =============================================================================
# EMU-GPU Toolkit v2.1 - Instalador GUI
# =============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="$HOME/.emu-gpu"
APPS_DIR="$HOME/.local/share/applications"
BIN_DIR="$HOME/.local/bin"

echo -e "${BOLD}${CYAN}"
echo "    ============================================"
echo "       EMU-GPU Toolkit v2.1 - Instalador GUI"
echo "       GPU via CPU + Tradutor de .exe"
echo "    ============================================"
echo -e "${NC}"

# ETAPA 0: Limpar versao antiga (v1.0)
echo ""
echo -e "${BOLD}${CYAN}[0/7] Limpando versao antiga...${NC}"
if [ -f "$SCRIPT_DIR/cleanup.sh" ]; then
    bash "$SCRIPT_DIR/cleanup.sh"
else
    # Limpeza manual basica
    rm -rf "$INSTALL_DIR/wrappers" "$INSTALL_DIR/venv" "$INSTALL_DIR/src" \
           "$INSTALL_DIR/activate" "$INSTALL_DIR/deactivate" 2>/dev/null || true
fi
echo ""

# Verificar sistema
echo -e "${BLUE}[INFO]${NC} Verificando sistema..."
CPU_CORES=$(nproc)
echo -e "  CPU: ${GREEN}$(grep 'model name' /proc/cpuinfo | head -1 | cut -d':' -f2 | xargs)${NC} (${CPU_CORES} threads)"

# ETAPA 1: Dependencias Python
echo ""
echo -e "${BOLD}${CYAN}[1/7] Instalando dependencias Python...${NC}"
sudo apt-get update -qq
sudo apt-get install -y -qq python3 python3-tk 2>&1 | tail -3
echo -e "  ${GREEN}OK${NC}"

# ETAPA 2: Mesa / Drivers GPU por software
echo ""
echo -e "${BOLD}${CYAN}[2/7] Instalando drivers de renderizacao por software...${NC}"
sudo apt-get install -y -qq \
    mesa-vulkan-drivers vulkan-tools libvulkan1 \
    mesa-utils libgl1-mesa-dri libglx-mesa0 \
    2>&1 | tail -3
echo -e "  ${GREEN}OK${NC}"

# ETAPA 3: Wine
echo ""
echo -e "${BOLD}${CYAN}[3/7] Instalando Wine...${NC}"
sudo dpkg --add-architecture i386 2>/dev/null || true
sudo apt-get update -qq
sudo apt-get install -y -qq wine64 wine32 winetricks 2>&1 | tail -5 || {
    echo -e "  ${YELLOW}Tentando alternativa...${NC}"
    sudo apt-get install -y -qq wine 2>&1 | tail -3 || true
}
if command -v wine &>/dev/null; then
    echo -e "  ${GREEN}OK${NC} ($(wine --version 2>/dev/null || echo "instalado"))"
else
    echo -e "  ${YELLOW}AVISO${NC} Wine nao instalado. O app funciona, mas .exe nao rodarao."
fi

# ETAPA 4: Utilitarios
echo ""
echo -e "${BOLD}${CYAN}[4/7] Instalando utilitarios...${NC}"
sudo apt-get install -y -qq taskset p7zip-full 2>&1 | tail -3 || true
echo -e "  ${GREEN}OK${NC}"

# ETAPA 5: Instalar app GUI
echo ""
echo -e "${BOLD}${CYAN}[5/7] Instalando EMU-GPU GUI v2.1...${NC}"
mkdir -p "$INSTALL_DIR"/{app,config,scripts,games,logs}
cp -r "$SCRIPT_DIR/app"/* "$INSTALL_DIR/app/"
cp -r "$SCRIPT_DIR/config"/* "$INSTALL_DIR/config/" 2>/dev/null || true
chmod +x "$INSTALL_DIR/app/launcher.sh"
echo -e "  ${GREEN}OK${NC} Instalado em $INSTALL_DIR"

# ETAPA 6: Criar atalhos
echo ""
echo -e "${BOLD}${CYAN}[6/7] Criando atalhos...${NC}"
mkdir -p "$BIN_DIR" "$APPS_DIR"

cat > "$BIN_DIR/emu-gpu" << 'EOF'
#!/bin/bash
export EMU_GPU_TOOLKIT="$HOME/.emu-gpu"
python3 "$HOME/.emu-gpu/app/emu_gpu_gui.py" "$@"
EOF
chmod +x "$BIN_DIR/emu-gpu"

# .desktop para menu de aplicativos
cat > "$APPS_DIR/emu-gpu-toolkit.desktop" << EOF
[Desktop Entry]
Name=EMU-GPU Toolkit
Comment=GPU via CPU - Executa jogos .exe sem placa de video
Exec=$BIN_DIR/emu-gpu
Type=Application
Terminal=false
Icon=application-x-executable
Categories=Game;System;
Keywords=game;gpu;cpu;exe;wine;emulator;
StartupNotify=true
EOF

# Copiar icone se existir
if [ -f "$SCRIPT_DIR/docs/icon.png" ]; then
    mkdir -p "$HOME/.local/share/icons"
    cp "$SCRIPT_DIR/docs/icon.png" "$HOME/.local/share/icons/emu-gpu.png"
    sed -i "s|Icon=.*|Icon=$HOME/.local/share/icons/emu-gpu.png|" "$APPS_DIR/emu-gpu-toolkit.desktop"
fi

update-desktop-database "$APPS_DIR" 2>/dev/null || true
echo -e "  ${GREEN}OK${NC}"

# ETAPA 7: Verificar
echo ""
echo -e "${BOLD}${CYAN}[7/7] Verificando instalacao...${NC}"
python3 -c "import tkinter; print('  tkinter OK')" 2>/dev/null || echo -e "  ${RED}tkinter FALHOU${NC}"

echo ""
echo -e "${BOLD}${GREEN}========================================${NC}"
echo -e "${BOLD}${GREEN}   Instalacao Concluida! (v2.1)${NC}"
echo -e "${BOLD}${GREEN}========================================${NC}"
echo ""
echo -e "Para abrir o EMU-GPU Toolkit:"
echo -e "  ${CYAN}1. Menu de Aplicativos${NC} -> 'EMU-GPU Toolkit'"
echo -e "  ${CYAN}2. Terminal${NC} -> digite: emu-gpu"
echo -e "  ${CYAN}3. Direto${NC} -> $INSTALL_DIR/app/launcher.sh"
echo ""
read -p "Deseja abrir agora? [S/n]: " abrir
if [[ ! "$abrir" =~ ^[Nn]$ ]]; then
    emu-gpu &
fi
