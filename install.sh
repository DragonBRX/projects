#!/bin/bash
# =============================================================================
# EMU-GPU TOOLKIT - Instalador Principal
# Uma ferramenta experimental para emular GPU via CPU e traduzir .exe no Ubuntu
# Para CPUs potentes com GPUs fracas (como Intel HD 3000)
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

echo -e "${BOLD}${CYAN}"
echo "    ╔══════════════════════════════════════════════════════════════╗"
echo "    ║           EMU-GPU TOOLKIT v1.0 - Instalador                 ║"
echo "    ║     GPU via CPU + Tradutor de .exe para Ubuntu               ║"
echo "    ╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"
echo ""

# Detectar hardware
echo -e "${BLUE}[INFO]${NC} Detectando hardware..."
CPU_MODEL=$(grep "model name" /proc/cpuinfo | head -1 | cut -d':' -f2 | xargs)
CPU_CORES=$(nproc)
CPU_THREADS=$(grep -c "^processor" /proc/cpuinfo)
RAM_GB=$(free -g | awk '/^Mem:/{print $2}')
GPU_INFO=$(lspci 2>/dev/null | grep -i "vga\|3d\|display" | head -1 | cut -d':' -f3 | xargs || echo "GPU não detectada via lspci")

echo -e "  ${GREEN}CPU:${NC}      $CPU_MODEL"
echo -e "  ${GREEN}Núcleos:${NC}  $CPU_CORES cores / $CPU_THREADS threads"
echo -e "  ${GREEN}RAM:${NC}      ${RAM_GB}GB"
echo -e "  ${GREEN}GPU:${NC}      $GPU_INFO"
echo ""

# Verificar sistema
echo -e "${BLUE}[INFO]${NC} Verificando sistema..."
if [ ! -f /etc/os-release ]; then
    echo -e "${RED}[ERRO]${NC} Não foi possível detectar a distribuição"
    exit 1
fi

source /etc/os-release
if [[ "$ID" != "ubuntu" && "$ID_LIKE" != *"ubuntu"* && "$ID" != "debian" && "$ID_LIKE" != *"debian"* ]]; then
    echo -e "${YELLOW}[AVISO]${NC} Sistema não é Ubuntu/Debian. Continuando mesmo assim..."
fi
echo -e "  ${GREEN}OS:${NC}       $PRETTY_NAME"
echo ""

# Verificar arquitetura
ARCH=$(uname -m)
if [ "$ARCH" != "x86_64" ]; then
    echo -e "${RED}[ERRO]${NC} Arquitetura $ARCH não suportada. Precisa ser x86_64."
    exit 1
fi

# Verificar permissões
echo -e "${BLUE}[INFO]${NC} Verificando permissões..."
if [ "$EUID" -eq 0 ]; then
    echo -e "${YELLOW}[AVISO]${NC} Não rode como root! O script pedirá sudo quando necessário."
    exit 1
fi

# Verificar sudo
if ! sudo -n true 2>/dev/null; then
    echo -e "${YELLOW}[AVISO]${NC} Você precisará digitar sua senha para instalar pacotes."
fi

# ============================================================================
# FUNÇÕES DE INSTALAÇÃO
# ============================================================================

install_base_packages() {
    echo -e "\n${BOLD}${CYAN}▶ ETAPA 1/6: Instalando pacotes base...${NC}"
    
    sudo apt-get update
    
    # Pacotes essenciais para compilação e funcionamento
    local PACKAGES=(
        # Compilação
        build-essential git cmake meson ninja-build
        # Vulkan e drivers Mesa
        mesa-vulkan-drivers vulkan-tools libvulkan1
        # OpenGL por software
        libgl1-mesa-dri libglx-mesa0 mesa-utils
        # Wine e dependências
        wine64 wine64-preloader winetricks
        # Utilitários
        htop inxi cpufrequtils cpulimit
        # Python e pip
        python3 python3-pip python3-venv
        # Bibliotecas 32-bit (para Wine e jogos antigos)
        libc6:i386 libncurses5:i386 libstdc++6:i386
        # Outras bibliotecas importantes
        libsdl2-2.0-0 libsdl2-image-2.0-0 libsdl2-mixer-2.0-0
        libopenal1 libvorbisfile3 libpng16-16 libjpeg-turbo8
        # Compressão
        p7zip-full unzip
        # X11 e display virtual (para headless)
        xvfb x11-xserver-utils
    )
    
    echo -e "${BLUE}[INFO]${NC} Instalando ${#PACKAGES[@]} pacotes..."
    sudo apt-get install -y "${PACKAGES[@]}" 2>&1 | tail -5
    
    echo -e "${GREEN}[OK]${NC} Pacotes base instalados."
}

install_mesa_llvmpipe() {
    echo -e "\n${BOLD}${CYAN}▶ ETAPA 2/6: Configurando Mesa LLVMpipe (GPU via CPU)...${NC}"
    
    # LLVMpipe é o driver OpenGL por software da Mesa
    # Ele usa a CPU para renderizar gráficos 3D via LLVM
    
    # Verificar se LLVMpipe está disponível
    if glxinfo 2>/dev/null | grep -q "llvmpipe"; then
        echo -e "${GREEN}[OK]${NC} LLVMpipe já detectado!"
    else
        echo -e "${YELLOW}[AVISO]${NC} LLVMpipe não detectado ainda, mas será configurado."
    fi
    
    # Lavapipe (Vulkan por software)
    if ! vulkaninfo --summary 2>/dev/null | grep -q "LAVAPIPE"; then
        echo -e "${YELLOW}[AVISO]${NC} Lavapipe não detectado. Tentando instalar..."
        sudo apt-get install -y mesa-vulkan-drivers 2>/dev/null || true
    fi
    
    # Criar wrappers otimizados
    mkdir -p "$INSTALL_DIR/wrappers"
    
    # Wrapper para OpenGL por software (LLVMpipe)
    cat > "$INSTALL_DIR/wrappers/llvmpipe-glx" << 'EOF'
#!/bin/bash
# Wrapper LLVMpipe - Força renderização OpenGL por CPU
export LIBGL_ALWAYS_SOFTWARE=1
export GALLIUM_DRIVER=llvmpipe
export LP_NUM_THREADS=0  # 0 = usa todos os threads disponíveis
export MESA_GL_VERSION_OVERRIDE=4.5
export MESA_GLSL_VERSION_OVERRIDE=450
exec "$@"
EOF
    chmod +x "$INSTALL_DIR/wrappers/llvmpipe-glx"
    
    # Wrapper para Vulkan por software (Lavapipe)
    cat > "$INSTALL_DIR/wrappers/lavapipe-vk" << 'EOF'
#!/bin/bash
# Wrapper Lavapipe - Força renderização Vulkan por CPU
export VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.x86_64.json
# Se não existir, tenta o genérico
[ ! -f "$VK_ICD_FILENAMES" ] && export VK_ICD_FILENAMES=$(find /usr -name "lvp_icd*.json" 2>/dev/null | head -1)
# Desabilita outras GPUs
export DRI_PRIME=0
export __GLX_VENDOR_LIBRARY_NAME=mesa
# Variáveis de otimização
export LVP_PIPE_OPTIONS="fp16=0"
exec "$@"
EOF
    chmod +x "$INSTALL_DIR/wrappers/lavapipe-vk"
    
    # Wrapper combinado (Vulkan + OpenGL por software)
    cat > "$INSTALL_DIR/wrappers/swrender-full" << 'EOF'
#!/bin/bash
# Wrapper Completo - Toda renderização via CPU
# OpenGL via LLVMpipe
export LIBGL_ALWAYS_SOFTWARE=1
export GALLIUM_DRIVER=llvmpipe
export LP_NUM_THREADS=0
export MESA_GL_VERSION_OVERRIDE=4.5
export MESA_GLSL_VERSION_OVERRIDE=450
# Vulkan via Lavapipe
export VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.x86_64.json
[ ! -f "$VK_ICD_FILENAMES" ] && export VK_ICD_FILENAMES=$(find /usr -name "lvp_icd*.json" 2>/dev/null | head -1)
# Desabilita GPU física
export DRI_PRIME=0
export __GLX_VENDOR_LIBRARY_NAME=mesa
# Zink (OpenGL sobre Vulkan) também por software
export MESA_LOADER_DRIVER_OVERRIDE=zink
# Otimizações de memória
export MESA_NO_ERROR=1
# Threading
export __GL_THREADED_OPTIMIZATIONS=1
exec "$@"
EOF
    chmod +x "$INSTALL_DIR/wrappers/swrender-full"
    
    echo -e "${GREEN}[OK]${NC} Wrappers de renderização por software criados."
}

install_wine_dxvk() {
    echo -e "\n${BOLD}${CYAN}▶ ETAPA 3/6: Configurando Wine + DXVK/VK3D...${NC}"
    
    # Verificar se Wine está instalado
    if ! command -v wine &>/dev/null; then
        echo -e "${YELLOW}[AVISO]${NC} Wine não encontrado. Tentando instalar..."
        
        # Habilitar arquitetura 32-bit
        sudo dpkg --add-architecture i386 2>/dev/null || true
        sudo apt-get update
        
        # Instalar Wine da repo oficial se possível
        sudo apt-get install -y wine64 wine32 || {
            echo -e "${YELLOW}[AVISO]${NC} Falha ao instalar via apt. Tentando método alternativo..."
            # Download manual do Wine
            WINE_VERSION="8.0.2"
            WINE_DEB="wine-${WINE_VERSION}-ubuntu-amd64.deb"
            cd /tmp
            wget -q "https://github.com/Kron4ek/Wine-Builds/releases/download/${WINE_VERSION}/${WINE_DEB}" -O "$WINE_DEB" 2>/dev/null || {
                echo -e "${RED}[ERRO]${NC} Não foi possível baixar o Wine."
                return 1
            }
            sudo dpkg -i "$WINE_DEB" || sudo apt-get install -f -y
        }
    fi
    
    WINE_VERSION=$(wine --version 2>/dev/null || echo "desconhecido")
    echo -e "  ${GREEN}Wine:${NC} $WINE_VERSION"
    
    # Inicializar prefixo Wine se não existir
    if [ ! -d "$HOME/.wine" ]; then
        echo -e "${BLUE}[INFO]${NC} Inicializando prefixo Wine (pode demorar)..."
        WINEARCH=win64 winecfg /v=win10 2>&1 | tail -3
    fi
    
    # Instalar Winetricks se não existir
    if ! command -v winetricks &>/dev/null; then
        echo -e "${BLUE}[INFO]${NC} Instalando winetricks..."
        sudo apt-get install -y winetricks 2>/dev/null || {
            wget -q https://raw.githubusercontent.com/Winetricks/winetricks/master/src/winetricks -O /tmp/winetricks
            chmod +x /tmp/winetricks
            sudo mv /tmp/winetricks /usr/local/bin/
        }
    fi
    
    # Baixar DXVK (DirectX 9/10/11 → Vulkan) - versão que funciona com Lavapipe
    echo -e "${BLUE}[INFO]${NC} Baixando DXVK (DirectX → Vulkan)..."
    DXVK_VERSION="2.3.1"
    DXVK_DIR="$INSTALL_DIR/dxvk"
    
    mkdir -p "$DXVK_DIR"
    cd "$DXVK_DIR"
    
    # DXVK mais recente que funciona bem com Lavapipe
    DXVK_URL="https://github.com/doitsujin/dxvk/releases/download/v${DXVK_VERSION}/dxvk-${DXVK_VERSION}.tar.gz"
    
    if [ ! -f "dxvk-${DXVK_VERSION}.tar.gz" ]; then
        wget -q --show-progress "$DXVK_URL" -O "dxvk-${DXVK_VERSION}.tar.gz" 2>&1 || {
            echo -e "${YELLOW}[AVISO]${NC} Falha ao baixar DXVK ${DXVK_VERSION}. Tentando versão alternativa..."
            # DXVK 1.10.3 é mais compatível com GPUs limitadas
            DXVK_VERSION="1.10.3"
            wget -q --show-progress "https://github.com/doitsujin/dxvk/releases/download/v${DXVK_VERSION}/dxvk-${DXVK_VERSION}.tar.gz" -O "dxvk-${DXVK_VERSION}.tar.gz"
        }
    fi
    
    tar -xzf "dxvk-${DXVK_VERSION}.tar.gz" 2>/dev/null || true
    echo -e "  ${GREEN}DXVK:${NC} v${DXVK_VERSION} disponível em $DXVK_DIR"
    
    # Criar script de instalação do DXVK no prefixo Wine
    cat > "$INSTALL_DIR/scripts/install-dxvk.sh" << EOF
#!/bin/bash
# Instala DXVK no prefixo Wine atual
DXVK_DIR="$INSTALL_DIR/dxvk/dxvk-${DXVK_VERSION}"
if [ -d "\$DXVK_DIR" ]; then
    WINEPREFIX=\${WINEPREFIX:-\$HOME/.wine}
    cp "\$DXVK_DIR"/x64/*.dll "\$WINEPREFIX/drive_c/windows/system32/" 2>/dev/null || true
    cp "\$DXVK_DIR"/x32/*.dll "\$WINEPREFIX/drive_c/windows/syswow64/" 2>/dev/null || true
    # Configurar overrides no registro
    wine reg add "HKCU\\Software\\Wine\\DllOverrides" /v d3d9 /d native /f >/dev/null 2>&1
    wine reg add "HKCU\\Software\\Wine\\DllOverrides" /v d3d10 /d native /f >/dev/null 2>&1
    wine reg add "HKCU\\Software\\Wine\\DllOverrides" /v d3d10_1 /d native /f >/dev/null 2>&1
    wine reg add "HKCU\\Software\\Wine\\DllOverrides" /v d3d10core /d native /f >/dev/null 2>&1
    wine reg add "HKCU\\Software\\Wine\\DllOverrides" /v d3d11 /d native /f >/dev/null 2>&1
    wine reg add "HKCU\\Software\\Wine\\DllOverrides" /v dxgi /d native /f >/dev/null 2>&1
    echo "DXVK instalado no prefixo \$WINEPREFIX"
else
    echo "DXVK não encontrado em \$DXVK_DIR"
    exit 1
fi
EOF
    chmod +x "$INSTALL_DIR/scripts/install-dxvk.sh"
    
    # VKD3D-Proton (DirectX 12 → Vulkan)
    echo -e "${BLUE}[INFO]${NC} Baixando VKD3D-Proton (DirectX 12 → Vulkan)..."
    VKD3D_VERSION="2.11.1"
    VKD3D_DIR="$INSTALL_DIR/vkd3d"
    
    mkdir -p "$VKD3D_DIR"
    cd "$VKD3D_DIR"
    
    if [ ! -f "vkd3d-proton-${VKD3D_VERSION}.tar.zst" ]; then
        wget -q --show-progress "https://github.com/HansKristian-Work/vkd3d-proton/releases/download/v${VKD3D_VERSION}/vkd3d-proton-${VKD3D_VERSION}.tar.zst" -O "vkd3d-proton-${VKD3D_VERSION}.tar.zst" 2>/dev/null || {
            echo -e "${YELLOW}[AVISO]${NC} Falha ao baixar VKD3D. Pulando..."
        }
    fi
    
    if [ -f "vkd3d-proton-${VKD3D_VERSION}.tar.zst" ]; then
        tar -xf "vkd3d-proton-${VKD3D_VERSION}.tar.zst" 2>/dev/null || true
        echo -e "  ${GREEN}VKD3D:${NC} v${VKD3D_VERSION} disponível"
    fi
    
    echo -e "${GREEN}[OK]${NC} Wine + DXVK/VKD3D configurados."
}

install_python_tool() {
    echo -e "\n${BOLD}${CYAN}▶ ETAPA 4/6: Instalando ferramenta Python emu-gpu...${NC}"
    
    # Criar ambiente virtual
    PYTHON_VENV="$INSTALL_DIR/venv"
    python3 -m venv "$PYTHON_VENV" 2>/dev/null || {
        echo -e "${YELLOW}[AVISO]${NC} python3-venv não disponível. Tentando sem venv..."
        PYTHON_VENV=""
    }
    
    # Instalar dependências
    if [ -n "$PYTHON_VENV" ]; then
        source "$PYTHON_VENV/bin/activate"
    fi
    
    pip install --upgrade pip -q
    pip install colorama psutil pyyaml -q
    
    # Copiar arquivos do toolkit
    cp -r "$SCRIPT_DIR/src" "$INSTALL_DIR/"
    cp -r "$SCRIPT_DIR/config" "$INSTALL_DIR/"
    
    # Criar launcher
    mkdir -p "$BIN_DIR"
    
    cat > "$BIN_DIR/emu-gpu" << EOF
#!/bin/bash
# Launcher para a ferramenta emu-gpu
INSTALL_DIR="$INSTALL_DIR"
PYTHON_VENV="$PYTHON_VENV"

if [ -n "\$PYTHON_VENV" ] && [ -f "\$PYTHON_VENV/bin/activate" ]; then
    source "\$PYTHON_VENV/bin/activate"
fi

export PYTHONPATH="\$INSTALL_DIR:\$PYTHONPATH"
python3 "\$INSTALL_DIR/src/emu_gpu.py" "\$@"
EOF
    chmod +x "$BIN_DIR/emu-gpu"
    
    # Criar .desktop entry
    mkdir -p "$DESKTOP_DIR"
    cat > "$DESKTOP_DIR/emu-gpu.desktop" << EOF
[Desktop Entry]
Name=EMU-GPU Toolkit
Comment=GPU via CPU e tradutor de .exe
Exec=$BIN_DIR/emu-gpu
Icon=$INSTALL_DIR/icon.png
Type=Application
Terminal=true
Categories=System;Utility;
EOF
    
    echo -e "${GREEN}[OK]${NC} Ferramenta emu-gpu instalada em $BIN_DIR/emu-gpu"
}

configure_optimizations() {
    echo -e "\n${BOLD}${CYAN}▶ ETAPA 5/6: Configurando otimizações de CPU...${NC}"
    
    # Script de otimização de CPU para jogos
    cat > "$INSTALL_DIR/scripts/cpu-governor-game.sh" << 'EOF'
#!/bin/bash
# Coloca CPU em modo performance para jogos
if [ "$EUID" -ne 0 ]; then
    echo "Rode com sudo para alterar governor"
    exit 1
fi

# Performance mode
for cpu in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
    echo performance > "$cpu" 2>/dev/null || true
done

# Desabilitar turboboost / speedstep se possível (mantém clock máximo)
if [ -f /sys/devices/system/cpu/intel_pstate/no_turbo ]; then
    echo 0 > /sys/devices/system/cpu/intel_pstate/no_turbo 2>/dev/null || true
fi

echo "CPU configurada para modo performance"
EOF
    chmod +x "$INSTALL_DIR/scripts/cpu-governor-game.sh"
    
    # Script para reverter
    cat > "$INSTALL_DIR/scripts/cpu-governor-powersave.sh" << 'EOF'
#!/bin/bash
# Volta CPU para modo powersave
if [ "$EUID" -ne 0 ]; then
    echo "Rode com sudo para alterar governor"
    exit 1
fi

for cpu in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
    echo powersave > "$cpu" 2>/dev/null || true
done

echo "CPU configurada para modo powersave"
EOF
    chmod +x "$INSTALL_DIR/scripts/cpu-governor-powersave.sh"
    
    # Script de afinidade de CPU (isola cores para jogos)
    cat > "$INSTALL_DIR/scripts/cpu-affinity-launcher.sh" << 'EOF'
#!/bin/bash
# Launcher com afinidade de CPU otimizada
# Isola cores físicos para o jogo, deixa threads lógicos para sistema

# Detectar layout de CPU
TOTAL_CORES=$(nproc)
if [ "$TOTAL_CORES" -eq 8 ]; then
    # 4 cores / 8 threads típico: usar cores 0,1,2,3 (físicos)
    AFFINITY_MASK="0,1,2,3"
    ISO_MASK="4,5,6,7"
elif [ "$TOTAL_CORES" -eq 4 ]; then
    # 2 cores / 4 threads: usar cores 0,1
    AFFINITY_MASK="0,1"
    ISO_MASK="2,3"
else
    # Genérico: usar metade dos cores
    AFFINITY_MASK="0-$((TOTAL_CORES/2-1))"
    ISO_MASK="$((TOTAL_CORES/2))-$((TOTAL_CORES-1))"
fi

echo "Máscara de afinidade: $AFFINITY_MASK (sistema: $ISO_MASK)"
taskset -c "$AFFINITY_MASK" "$@"
EOF
    chmod +x "$INSTALL_DIR/scripts/cpu-affinity-launcher.sh"
    
    # Script de limitação de FPS (reduz carga na CPU)
    cat > "$INSTALL_DIR/scripts/fps-limiter.sh" << 'EOF'
#!/bin/bash
# Limita FPS para reduzir carga de CPU em renderização por software
FPS_LIMIT=${1:-30}
shift

echo "Limitando a $FPS_LIMIT FPS..."
# Usa libstrangle se disponível, senão fallback para outras formas
if command -v strangle &>/dev/null; then
    strangle "$FPS_LIMIT" "$@"
else
    # Fallback: exporta variável que alguns jogos respeitam
    export __GL_SYNC_TO_VBLANK=1
    export vblank_mode=1
    # Tentar usar mangohud como limitador
    if command -v mangohud &>/dev/null; then
        MANGOHUD_CONFIG=fps_limit=$FPS_LIMIT mangohud "$@"
    else
        "$@"
    fi
fi
EOF
    chmod +x "$INSTALL_DIR/scripts/fps-limiter.sh"
    
    echo -e "${GREEN}[OK]${NC} Otimizações de CPU configuradas."
}

setup_environment() {
    echo -e "\n${BOLD}${CYAN}▶ ETAPA 6/6: Configurando ambiente do usuário...${NC}"
    
    # Adicionar ao .bashrc se não existir
    if ! grep -q "EMU_GPU_TOOLKIT" "$HOME/.bashrc" 2>/dev/null; then
        cat >> "$HOME/.bashrc" << EOF

# === EMU-GPU TOOLKIT ===
export EMU_GPU_TOOLKIT="$INSTALL_DIR"
export PATH="$BIN_DIR:\$PATH"
alias swrender="$INSTALL_DIR/wrappers/swrender-full"
alias llvmpipe="$INSTALL_DIR/wrappers/llvmpipe-glx"
alias lavapipe="$INSTALL_DIR/wrappers/lavapipe-vk"
alias game-mode="sudo $INSTALL_DIR/scripts/cpu-governor-game.sh"
alias powersave-mode="sudo $INSTALL_DIR/scripts/cpu-governor-powersave.sh"
# ========================
EOF
        echo -e "${GREEN}[OK]${NC} Aliases adicionados ao .bashrc"
    fi
    
    # Criar diretório para jogos
    mkdir -p "$HOME/Games/exe-translated"
    
    # Script de ativação do ambiente
    cat > "$INSTALL_DIR/activate" << EOF
#!/bin/bash
# Ativa o ambiente EMU-GPU no shell atual
export EMU_GPU_TOOLKIT="$INSTALL_DIR"
export PATH="$BIN_DIR:\$PATH"
export LIBGL_ALWAYS_SOFTWARE=1
export GALLIUM_DRIVER=llvmpipe
export LP_NUM_THREADS=0
export VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.x86_64.json
[ ! -f "\$VK_ICD_FILENAMES" ] && export VK_ICD_FILENAMES=\$(find /usr -name "lvp_icd*.json" 2>/dev/null | head -1)
export MESA_GL_VERSION_OVERRIDE=4.5
echo "Ambiente EMU-GPU ativado!"
echo "Para desativar, feche o terminal ou rode: deactivate-emu"
EOF
    chmod +x "$INSTALL_DIR/activate"
    
    cat > "$INSTALL_DIR/deactivate" << 'EOF'
#!/bin/bash
# Desativa o ambiente EMU-GPU
unset EMU_GPU_TOOLKIT
unset LIBGL_ALWAYS_SOFTWARE
unset GALLIUM_DRIVER
unset LP_NUM_THREADS
unset VK_ICD_FILENAMES
unset MESA_GL_VERSION_OVERRIDE
echo "Ambiente EMU-GPU desativado."
EOF
    chmod +x "$INSTALL_DIR/deactivate"
    
    # Baixar ícone genérico
    cp "$SCRIPT_DIR/docs/icon.png" "$INSTALL_DIR/icon.png" 2>/dev/null || \
        touch "$INSTALL_DIR/icon.png"
    
    echo -e "${GREEN}[OK]${NC} Ambiente configurado."
}

# ============================================================================
# EXECUÇÃO PRINCIPAL
# ============================================================================

main() {
    echo -e "${BOLD}Iniciando instalação...${NC}"
    echo ""
    
    # Criar diretórios
    mkdir -p "$INSTALL_DIR"/{scripts,wrappers,config,games,logs}
    
    # Rodar etapas
    install_base_packages
    install_mesa_llvmpipe
    install_wine_dxvk
    install_python_tool
    configure_optimizations
    setup_environment
    
    # Resumo
    echo -e "\n${BOLD}${GREEN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${BOLD}${GREEN}  ✓ INSTALAÇÃO CONCLUÍDA!${NC}"
    echo -e "${BOLD}${GREEN}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "${BOLD}Comandos disponíveis:${NC}"
    echo -e "  ${CYAN}emu-gpu${NC}                  - Ferramenta principal (CLI)"
    echo -e "  ${CYAN}swrender <programa>${NC}      - Roda programa com GPU via CPU"
    echo -e "  ${CYAN}llvmpipe <programa>${NC}      - Roda com OpenGL por software"
    echo -e "  ${CYAN}lavapipe <programa>${NC}      - Roda com Vulkan por software"
    echo -e "  ${CYAN}game-mode${NC}                - Ativa modo performance da CPU"
    echo -e "  ${CYAN}powersave-mode${NC}           - Volta CPU para economia"
    echo ""
    echo -e "${BOLD}Para ativar o ambiente:${NC}"
    echo -e "  ${CYAN}source ~/.emu-gpu/activate${NC}"
    echo ""
    echo -e "${BOLD}Para usar agora:${NC}"
    echo -e "  1. ${CYAN}source ~/.bashrc${NC}  (ou abra um novo terminal)"
    echo -e "  2. ${CYAN}emu-gpu --help${NC}   (ver todos os comandos)"
    echo -e "  3. ${CYAN}emu-gpu run-cpu <seu-jogo.exe>${NC}"
    echo ""
    echo -e "${YELLOW}AVISO:${NC} Reinicie o terminal ou rode 'source ~/.bashrc' para"
    echo -e "        usar os comandos imediatamente."
    echo ""
    echo -e "${BOLD}${GREEN}═══════════════════════════════════════════════════════════════${NC}"
}

# Verificar argumentos
if [ "$1" == "--help" ] || [ "$1" == "-h" ]; then
    echo "EMU-GPU Toolkit - Instalador"
    echo ""
    echo "Uso: ./install.sh [opções]"
    echo ""
    echo "Este script instala:"
    echo "  - Drivers Mesa LLVMpipe (OpenGL por CPU)"
    echo "  - Drivers Lavapipe (Vulkan por CPU)"
    echo "  - Wine + DXVK + VKD3D (tradução .exe)"
    echo "  - Ferramenta CLI emu-gpu"
    echo "  - Otimizações de CPU para jogos"
    echo ""
    echo "Requisitos: Ubuntu/Debian, CPU x86_64, 4GB+ RAM"
    exit 0
fi

# Confirmar instalação
echo -e "${YELLOW}Este script irá:${NC}"
echo "  1. Instalar pacotes do sistema (requer sudo)"
echo "  2. Configurar renderização GPU via CPU"
echo "  3. Instalar Wine + tradutores DirectX"
echo "  4. Criar ferramenta emu-gpu"
echo ""
read -p "Continuar? [S/n]: " CONFIRM
if [[ "$CONFIRM" =~ ^[Nn]$ ]]; then
    echo "Instalação cancelada."
    exit 0
fi

main
