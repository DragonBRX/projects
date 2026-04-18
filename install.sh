#!/bin/bash
# =============================================================================
# EMU-GPU TOOLKIT v2.0 - Instalador
# GPU via CPU + Traducao Propria de .exe para Ubuntu/Linux
# Nao usa Wine como aplicativo - usa codigo-fonte open-source
# =============================================================================

set -e

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="$HOME/.emu-gpu"
BIN_DIR="$HOME/.local/bin"
DESKTOP_DIR="$HOME/.local/share/applications"

# =============================================================================
# BANNER
# =============================================================================
echo -e "${BOLD}${CYAN}"
echo "    ╔══════════════════════════════════════════════════════════════════╗"
echo "    ║                EMU-GPU TOOLKIT v2.0 - Instalador               ║"
echo "    ║          GPU via CPU + Traducao Propria de .exe                ║"
echo "    ║                                                                  ║"
echo "    ║  NOVO v2.0:                                                     ║"
echo "    ║  - Interface GTK4/libadwaita (estilo Steam/Lutris)              ║"
echo "    ║  - Traducao propria (DXVK, VKD3D, FAudio - codigo aberto)      ║"
echo "    ║  - Nao usa Wine como app, apenas bibliotecas de traducao       ║"
echo "    ║  - Explorador de arquivos nativo (Nautilus)                    ║"
echo "    ║  - Ferramentas experimentais (FSR, Frame Generation)            ║"
echo "    ╚══════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"
echo ""

# =============================================================================
# DETECTAR HARDWARE
# =============================================================================
echo -e "${BLUE}[INFO]${NC} Detectando hardware..."
CPU_MODEL=$(grep "model name" /proc/cpuinfo | head -1 | cut -d':' -f2 | xargs)
CPU_CORES=$(nproc)
CPU_THREADS=$(grep -c "^processor" /proc/cpuinfo)
RAM_GB=$(free -g | awk '/^Mem:/{print $2}')
GPU_INFO=$(lspci 2>/dev/null | grep -i "vga\|3d\|display" | head -1 | cut -d':' -f3 | xargs || echo "GPU nao detectada")

echo -e "  ${GREEN}CPU:${NC}       $CPU_MODEL"
echo -e "  ${GREEN}Nucleos:${NC}   $CPU_CORES cores / $CPU_THREADS threads"
echo -e "  ${GREEN}RAM:${NC}       ${RAM_GB}GB"
echo -e "  ${GREEN}GPU:${NC}       $GPU_INFO"
echo ""

# =============================================================================
# VERIFICAR SISTEMA
# =============================================================================
echo -e "${BLUE}[INFO]${NC} Verificando sistema..."

if [ ! -f /etc/os-release ]; then
    echo -e "${RED}[ERRO]${NC} Nao foi possivel detectar a distribuicao"
    exit 1
fi

source /etc/os-release
if [[ "$ID" != "ubuntu" && "$ID_LIKE" != *"ubuntu"* && "$ID" != "debian" && "$ID_LIKE" != *"debian"* ]]; then
    echo -e "${YELLOW}[AVISO]${NC} Sistema nao e Ubuntu/Debian. Continuando mesmo assim..."
fi
echo -e "  ${GREEN}OS:${NC}        $PRETTY_NAME"
echo ""

ARCH=$(uname -m)
if [ "$ARCH" != "x86_64" ]; then
    echo -e "${RED}[ERRO]${NC} Arquitetura $ARCH nao suportada. Precisa ser x86_64."
    exit 1
fi

# Verificar permissoes
if [ "$EUID" -eq 0 ]; then
    echo -e "${YELLOW}[AVISO]${NC} Nao rode como root! O script pedira sudo quando necessario."
    exit 1
fi

# =============================================================================
# FUNCOES DE INSTALACAO
# =============================================================================

install_gtk4_deps() {
    echo -e "\n${BOLD}${CYAN}▶ ETAPA 1/7: Instalando dependencias GTK4/libadwaita...${NC}"
    
    sudo apt-get update
    
    local PACKAGES=(
        # GTK4 e libadwaita
        libgtk-4-1
        libadwaita-1-0
        gir1.2-gtk-4.0
        gir1.2-adw-1
        python3-gi
        python3-gi-cairo
        
        # Explorador de arquivos nativo
        nautilus
        zenity
        
        # Vulkan e drivers Mesa
        mesa-vulkan-drivers
        vulkan-tools
        libvulkan1
        vulkan-validationlayers
        
        # OpenGL por software
        libgl1-mesa-dri
        libglx-mesa0
        mesa-utils
        
        # Utilitarios
        htop
        inxi
        cpufrequtils
        
        # Python
        python3
        python3-pip
        
        # Bibliotecas
        libsdl2-2.0-0
        libopenal1
        libvorbisfile3
        libpng16-16
        libjpeg-turbo8
        
        # Audio
        libfaudio0
        libasound2-plugins
        
        # Compressao
        p7zip-full
        unzip
        
        # Compilacao
        build-essential
        cmake
        
        # Wine (apenas para bibliotecas, nao como app principal)
        wine64
        libwine
        
        # Outros
        xdg-utils
        desktop-file-utils
    )
    
    echo -e "${BLUE}[INFO]${NC} Instalando ${#PACKAGES[@]} pacotes..."
    sudo apt-get install -y "${PACKAGES[@]}" 2>&1 | tail -5
    
    echo -e "${GREEN}[OK]${NC} Dependencias GTK4/libadwaita instaladas."
}

install_mesa_llvmpipe() {
    echo -e "\n${BOLD}${CYAN}▶ ETAPA 2/7: Configurando Mesa LLVMpipe (GPU via CPU)...${NC}"
    
    # Verificar se LLVMpipe esta disponivel
    if glxinfo 2>/dev/null | grep -q "llvmpipe"; then
        echo -e "${GREEN}[OK]${NC} LLVMpipe detectado!"
    else
        echo -e "${YELLOW}[AVISO]${NC} LLVMpipe nao detectado ainda, mas sera configurado."
    fi
    
    # Lavapipe (Vulkan por software)
    if ! vulkaninfo --summary 2>/dev/null | grep -q "LAVAPIPE"; then
        echo -e "${YELLOW}[AVISO]${NC} Lavapipe nao detectado. Tentando instalar..."
        sudo apt-get install -y mesa-vulkan-drivers 2>/dev/null || true
    fi
    
    # Wrappers otimizados
    mkdir -p "$INSTALL_DIR/wrappers"
    
    # Wrapper LLVMpipe
    cat > "$INSTALL_DIR/wrappers/llvmpipe-glx" << 'EOF'
#!/bin/bash
export LIBGL_ALWAYS_SOFTWARE=1
export GALLIUM_DRIVER=llvmpipe
export LP_NUM_THREADS=0
export MESA_GL_VERSION_OVERRIDE=4.5
export MESA_GLSL_VERSION_OVERRIDE=450
export MESA_NO_ERROR=1
export __GL_THREADED_OPTIMIZATIONS=1
exec "$@"
EOF
    chmod +x "$INSTALL_DIR/wrappers/llvmpipe-glx"
    
    # Wrapper Lavapipe
    cat > "$INSTALL_DIR/wrappers/lavapipe-vk" << 'EOF'
#!/bin/bash
export VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.x86_64.json
[ ! -f "$VK_ICD_FILENAMES" ] && export VK_ICD_FILENAMES=$(find /usr -name "lvp_icd*.json" 2>/dev/null | head -1)
export DRI_PRIME=0
export __GLX_VENDOR_LIBRARY_NAME=mesa
export LVP_PIPE_OPTIONS="fp16=0"
exec "$@"
EOF
    chmod +x "$INSTALL_DIR/wrappers/lavapipe-vk"
    
    # Wrapper Completo
    cat > "$INSTALL_DIR/wrappers/swrender-full" << 'EOF'
#!/bin/bash
export LIBGL_ALWAYS_SOFTWARE=1
export GALLIUM_DRIVER=llvmpipe
export LP_NUM_THREADS=0
export MESA_GL_VERSION_OVERRIDE=4.5
export MESA_GLSL_VERSION_OVERRIDE=450
export MESA_LOADER_DRIVER_OVERRIDE=zink
export VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.x86_64.json
[ ! -f "$VK_ICD_FILENAMES" ] && export VK_ICD_FILENAMES=$(find /usr -name "lvp_icd*.json" 2>/dev/null | head -1)
export DRI_PRIME=0
export __GLX_VENDOR_LIBRARY_NAME=mesa
export MESA_NO_ERROR=1
export __GL_THREADED_OPTIMIZATIONS=1
exec "$@"
EOF
    chmod +x "$INSTALL_DIR/wrappers/swrender-full"
    
    echo -e "${GREEN}[OK]${NC} Wrappers de renderizacao configurados."
}

install_translators() {
    echo -e "\n${BOLD}${CYAN}▶ ETAPA 3/7: Instalando modulos de traducao...${NC}"
    
    mkdir -p "$INSTALL_DIR/translator"
    
    # DXVK
    echo -e "${BLUE}[INFO]${NC} Instalando DXVK..."
    DXVK_VERSION="2.3.1"
    DXVK_DIR="$INSTALL_DIR/translator/dxvk"
    mkdir -p "$DXVK_DIR"
    
    cd "$DXVK_DIR"
    if [ ! -f "dxvk-${DXVK_VERSION}.tar.gz" ]; then
        wget -q --show-progress "https://github.com/doitsujin/dxvk/releases/download/v${DXVK_VERSION}/dxvk-${DXVK_VERSION}.tar.gz" 2>&1 || {
            echo -e "${YELLOW}[AVISO]${NC} Falha no download do DXVK. Tentando versao alternativa..."
            DXVK_VERSION="1.10.3"
            wget -q --show-progress "https://github.com/doitsujin/dxvk/releases/download/v${DXVK_VERSION}/dxvk-${DXVK_VERSION}.tar.gz" 2>&1
        }
    fi
    
    if [ -f "dxvk-${DXVK_VERSION}.tar.gz" ]; then
        tar -xzf "dxvk-${DXVK_VERSION}.tar.gz" 2>/dev/null || true
        mkdir -p dlls/x64 dlls/x32
        if [ -d "dxvk-${DXVK_VERSION}/x64" ]; then
            cp dxvk-${DXVK_VERSION}/x64/*.dll dlls/x64/ 2>/dev/null || true
            cp dxvk-${DXVK_VERSION}/x32/*.dll dlls/x32/ 2>/dev/null || true
        fi
        echo -e "${GREEN}[OK]${NC} DXVK v${DXVK_VERSION} instalado."
    else
        echo -e "${YELLOW}[AVISO]${NC} DXVK nao pode ser baixado. Sera instalado depois."
    fi
    
    # VKD3D-Proton
    echo -e "${BLUE}[INFO]${NC} Instalando VKD3D-Proton..."
    VKD3D_VERSION="2.11.1"
    VKD3D_DIR="$INSTALL_DIR/translator/vkd3d"
    mkdir -p "$VKD3D_DIR"
    
    cd "$VKD3D_DIR"
    if [ ! -f "vkd3d-proton-${VKD3D_VERSION}.tar.zst" ]; then
        wget -q --show-progress "https://github.com/HansKristian-Work/vkd3d-proton/releases/download/v${VKD3D_VERSION}/vkd3d-proton-${VKD3D_VERSION}.tar.zst" 2>/dev/null || {
            echo -e "${YELLOW}[AVISO]${NC} Falha no download do VKD3D."
        }
    fi
    
    if [ -f "vkd3d-proton-${VKD3D_VERSION}.tar.zst" ]; then
        tar -xf "vkd3d-proton-${VKD3D_VERSION}.tar.zst" 2>/dev/null || true
        echo -e "${GREEN}[OK]${NC} VKD3D-Proton v${VKD3D_VERSION} instalado."
    else
        echo -e "${YELLOW}[AVISO]${NC} VKD3D nao pode ser baixado. Sera instalado depois."
    fi
    
    # FAudio
    echo -e "${BLUE}[INFO]${NC} Verificando FAudio..."
    if dpkg -l | grep -q libfaudio0; then
        echo -e "${GREEN}[OK]${NC} FAudio ja instalado."
    else
        echo -e "${YELLOW}[AVISO]${NC} FAudio nao encontrado. Instalando..."
        sudo apt-get install -y libfaudio0 2>/dev/null || true
    fi
    
    echo -e "${GREEN}[OK]${NC} Modulos de traducao configurados."
}

install_wine_libs() {
    echo -e "\n${BOLD}${CYAN}▶ ETAPA 4/7: Configurando Wine (apenas bibliotecas)...${NC}"
    
    if ! command -v wine &>/dev/null; then
        echo -e "${YELLOW}[AVISO]${NC} Wine nao encontrado. Instalando bibliotecas..."
        sudo dpkg --add-architecture i386 2>/dev/null || true
        sudo apt-get update
        sudo apt-get install -y wine64 libwine 2>&1 | tail -3
    fi
    
    WINE_VERSION=$(wine --version 2>/dev/null || echo "desconhecido")
    echo -e "  ${GREEN}Wine:${NC} $WINE_VERSION (apenas para bibliotecas DLL)"
    
    # Inicializar prefixo Wine se nao existir
    if [ ! -d "$HOME/.wine" ]; then
        echo -e "${BLUE}[INFO]${NC} Inicializando prefixo Wine..."
        WINEARCH=win64 winecfg /v=win10 2>&1 | tail -3
    fi
    
    echo -e "${GREEN}[OK]${NC} Wine configurado como backend de bibliotecas."
}

install_app() {
    echo -e "\n${BOLD}${CYAN}▶ ETAPA 5/7: Instalando EMU-GPU Toolkit v2.0...${NC}"
    
    # Criar diretorios
    mkdir -p "$INSTALL_DIR"/{app,app/core,app/pages,app/widgets,config,cache,logs,games}
    
    # Copiar arquivos do app
    cp -r "$SCRIPT_DIR/app"/* "$INSTALL_DIR/app/"
    
    # Criar launcher
    mkdir -p "$BIN_DIR"
    
    cat > "$BIN_DIR/emu-gpu" << 'EOF'
#!/bin/bash
# EMU-GPU Toolkit v2.0 Launcher
INSTALL_DIR="$HOME/.emu-gpu"
APP_DIR="$INSTALL_DIR/app"

cd "$APP_DIR"
python3 main.py "$@"
EOF
    chmod +x "$BIN_DIR/emu-gpu"
    
    # Criar .desktop
    mkdir -p "$DESKTOP_DIR"
    cat > "$DESKTOP_DIR/emu-gpu.desktop" << EOF
[Desktop Entry]
Name=EMU-GPU Toolkit
Name[pt_BR]=EMU-GPU Toolkit
Comment=GPU via CPU + Traducao de .exe
Comment[pt_BR]=GPU via CPU + Traducao de jogos .exe
Exec=$BIN_DIR/emu-gpu
Icon=$INSTALL_DIR/icon.png
Type=Application
Terminal=false
Categories=Game;Utility;
Keywords=game;emulator;gpu;wine;dxvk;
EOF
    
    # Copiar icone (ou criar um placeholder)
    if [ -f "$SCRIPT_DIR/config/icon.png" ]; then
        cp "$SCRIPT_DIR/config/icon.png" "$INSTALL_DIR/icon.png"
    else
        touch "$INSTALL_DIR/icon.png"
    fi
    
    # Configuracao inicial
    cat > "$INSTALL_DIR/config/settings.json" << 'EOF'
{
  "version": "2.0",
  "default_renderer": "swrender-full",
  "fps_limit": 30,
  "resolucao": "1280x720",
  "cpu_affinity": true,
  "game_mode": false,
  "janela": true,
  "ultimo_diretorio": "/home",
  "translators_ativos": ["dxvk", "faudio"],
  "experimental_tools": {
    "fsr": false,
    "frame_gen": false,
    "shader_cache": true
  },
  "theme": "dark",
  "notifications": true
}
EOF
    
    echo -e "${GREEN}[OK]${NC} EMU-GPU Toolkit v2.0 instalado em $INSTALL_DIR"
}

configure_optimizations() {
    echo -e "\n${BOLD}${CYAN}▶ ETAPA 6/7: Configurando otimizacoes...${NC}"
    
    # Script de game mode
    cat > "$INSTALL_DIR/scripts/cpu-governor-game.sh" << 'EOF'
#!/bin/bash
if [ "$EUID" -ne 0 ]; then
    echo "Rode com sudo"
    exit 1
fi
for cpu in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
    echo performance > "$cpu" 2>/dev/null || true
done
echo "CPU: modo performance"
EOF
    chmod +x "$INSTALL_DIR/scripts/cpu-governor-game.sh"
    
    # Script powersave
    cat > "$INSTALL_DIR/scripts/cpu-governor-powersave.sh" << 'EOF'
#!/bin/bash
if [ "$EUID" -ne 0 ]; then
    echo "Rode com sudo"
    exit 1
fi
for cpu in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
    echo powersave > "$cpu" 2>/dev/null || true
done
echo "CPU: modo powersave"
EOF
    chmod +x "$INSTALL_DIR/scripts/cpu-governor-powersave.sh"
    
    echo -e "${GREEN}[OK]${NC} Otimizacoes configuradas."
}

setup_environment() {
    echo -e "\n${BOLD}${CYAN}▶ ETAPA 7/7: Configurando ambiente...${NC}"
    
    # Adicionar ao .bashrc
    if ! grep -q "EMU_GPU_TOOLKIT" "$HOME/.bashrc" 2>/dev/null; then
        cat >> "$HOME/.bashrc" << EOF

# === EMU-GPU TOOLKIT v2.0 ===
export EMU_GPU_TOOLKIT="$INSTALL_DIR"
export PATH="$BIN_DIR:\$PATH"
alias emu-gpu="$BIN_DIR/emu-gpu"
alias swrender="$INSTALL_DIR/wrappers/swrender-full"
alias llvmpipe="$INSTALL_DIR/wrappers/llvmpipe-glx"
alias lavapipe="$INSTALL_DIR/wrappers/lavapipe-vk"
alias game-mode="sudo $INSTALL_DIR/scripts/cpu-governor-game.sh"
alias powersave-mode="sudo $INSTALL_DIR/scripts/cpu-governor-powersave.sh"
# =============================
EOF
        echo -e "${GREEN}[OK]${NC} Aliases adicionados ao .bashrc"
    fi
    
    # Criar diretorio de jogos
    mkdir -p "$HOME/Games/emu-gpu-library"
    
    # Script de ativacao
    cat > "$INSTALL_DIR/activate" << EOF
#!/bin/bash
export EMU_GPU_TOOLKIT="$INSTALL_DIR"
export PATH="$BIN_DIR:\$PATH"
echo "EMU-GPU Toolkit v2.0 ativado!"
echo "Comandos: emu-gpu, swrender, llvmpipe, lavapipe, game-mode"
EOF
    chmod +x "$INSTALL_DIR/activate"
    
    # Update desktop database
    update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
    
    echo -e "${GREEN}[OK]${NC} Ambiente configurado."
}

# =============================================================================
# EXECUCAO PRINCIPAL
# =============================================================================

main() {
    echo -e "${BOLD}Iniciando instalacao do EMU-GPU Toolkit v2.0...${NC}"
    echo ""
    
    # Criar diretorios
    mkdir -p "$INSTALL_DIR"/{scripts,wrappers,config,games,logs,translator}
    
    # Rodar etapas
    install_gtk4_deps
    install_mesa_llvmpipe
    install_translators
    install_wine_libs
    install_app
    configure_optimizations
    setup_environment
    
    # Resumo
    echo ""
    echo -e "${BOLD}${GREEN}════════════════════════════════════════════════════════════════${NC}"
    echo -e "${BOLD}${GREEN}  ✓ INSTALACAO CONCLUIDA!${NC}"
    echo -e "${BOLD}${GREEN}════════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "${BOLD}O que ha de novo na v2.0:${NC}"
    echo -e "  ${CYAN}•${NC} Interface GTK4/libadwaita (estilo Steam/Lutris)"
    echo -e "  ${CYN}•${NC} Traducao propria com DXVK, VKD3D, FAudio (codigo aberto)"
    echo -e "  ${CYAN}•${NC} Nao depende do Wine como aplicativo"
    echo -e "  ${CYAN}•${NC} Explorador de arquivos nativo (Nautilus)"
    echo -e "  ${CYAN}•${NC} Ferramentas experimentais (FSR, Frame Generation)"
    echo ""
    echo -e "${BOLD}Como usar:${NC}"
    echo -e "  1. ${CYAN}source ~/.bashrc${NC}  (ou abra um novo terminal)"
    echo -e "  2. ${CYAN}emu-gpu${NC}          (inicia a interface grafica)"
    echo ""
    echo -e "${BOLD}Atalhos criados:${NC}"
    echo -e "  ${CYAN}emu-gpu${NC}              - Interface grafica"
    echo -e "  ${CYAN}swrender <programa>${NC}  - Render completo por CPU"
    echo -e "  ${CYAN}game-mode${NC}            - Ativa performance maxima CPU"
    echo ""
    echo -e "${YELLOW}AVISO:${NC} Reinicie o terminal ou rode 'source ~/.bashrc' para"
    echo -e "        usar os comandos imediatamente."
    echo ""
    echo -e "${BOLD}${GREEN}════════════════════════════════════════════════════════════════${NC}"
}

# Verificar argumentos
if [ "$1" == "--help" ] || [ "$1" == "-h" ]; then
    echo "EMU-GPU Toolkit v2.0 - Instalador"
    echo ""
    echo "Uso: ./install.sh"
    echo ""
    echo "O EMU-GPU Toolkit v2.0 instala:"
    echo "  - Interface GTK4/libadwaita (moderna, estilo Steam)"
    echo "  - Drivers Mesa LLVMpipe/Lavapipe (GPU via CPU)"
    echo "  - Modulos de traducao: DXVK, VKD3D-Proton, FAudio"
    echo "  - Wine (apenas bibliotecas DLL, nao como app principal)"
    echo "  - Otimizacoes de CPU para jogos"
    echo ""
    echo "Requisitos: Ubuntu/Debian, CPU x86_64, 4GB+ RAM, GTK4"
    exit 0
fi

# Confirmar instalacao
echo -e "${YELLOW}Este script ira:${NC}"
echo "  1. Instalar GTK4, libadwaita, Nautilus, Vulkan"
echo "  2. Configurar renderizacao GPU via CPU (LLVMpipe/Lavapipe)"
echo "  3. Instalar modulos de traducao (DXVK, VKD3D, FAudio)"
echo "  4. Instalar EMU-GPU Toolkit v2.0"
echo "  5. Configurar otimizacoes de CPU"
echo ""
read -p "Continuar? [S/n]: " CONFIRM
if [[ "$CONFIRM" =~ ^[Nn]$ ]]; then
    echo "Instalacao cancelada."
    exit 0
fi

main
