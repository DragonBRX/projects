#!/bin/bash
# =============================================================================
# EMU-GPU Quick Translate
# Script rápido para traduzir e rodar .exe sem instalação formal
# =============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

INSTALL_DIR="${EMU_GPU_TOOLKIT:-$HOME/.emu-gpu}"

show_help() {
    echo -e "${BOLD}${CYAN}EMU-GPU Quick Translate${NC}"
    echo ""
    echo "Uso: $0 <arquivo.exe> [opções]"
    echo ""
    echo "Opções:"
    echo "  --opengl        Usar apenas OpenGL por software (LLVMpipe)"
    echo "  --vulkan        Usar apenas Vulkan por software (Lavapipe)"
    echo "  --full          Usar renderização completa por software (padrão)"
    echo "  --fps N         Limitar a N FPS"
    echo "  --cores N       Usar apenas N cores físicos"
    echo "  --windowed      Forçar modo janela"
    echo "  --resolution WxH Definir resolução"
    echo "  --debug         Modo debug com logs detalhados"
    echo ""
    echo "Exemplos:"
    echo "  $0 jogo.exe"
    echo "  $0 jogo.exe --opengl --fps 30"
    echo "  $0 jogo.exe --full --cores 2 --resolution 1280x720"
}

if [ $# -lt 1 ]; then
    show_help
    exit 1
fi

EXE_PATH=""
MODE="full"
FPS_LIMIT=0
CORES=0
WINDOWED=0
RESOLUTION=""
DEBUG=0
EXTRA_ARGS=()

# Parse argumentos
while [[ $# -gt 0 ]]; do
    case $1 in
        --help|-h)
            show_help
            exit 0
            ;;
        --opengl)
            MODE="opengl"
            shift
            ;;
        --vulkan)
            MODE="vulkan"
            shift
            ;;
        --full)
            MODE="full"
            shift
            ;;
        --fps)
            FPS_LIMIT="$2"
            shift 2
            ;;
        --cores)
            CORES="$2"
            shift 2
            ;;
        --windowed)
            WINDOWED=1
            shift
            ;;
        --resolution)
            RESOLUTION="$2"
            shift 2
            ;;
        --debug)
            DEBUG=1
            shift
            ;;
        -*)
            EXTRA_ARGS+=("$1")
            shift
            ;;
        *)
            if [ -z "$EXE_PATH" ]; then
                EXE_PATH="$1"
            else
                EXTRA_ARGS+=("$1")
            fi
            shift
            ;;
    esac
done

# Verificar arquivo
if [ ! -f "$EXE_PATH" ]; then
    echo -e "${RED}[ERRO]${NC} Arquivo não encontrado: $EXE_PATH"
    exit 1
fi

EXE_NAME=$(basename "$EXE_PATH")
EXE_DIR=$(dirname "$EXE_PATH")

echo -e "${BOLD}${CYAN}"
echo "  ╔════════════════════════════════════════════╗"
echo "  ║      EMU-GPU Quick Translate               ║"
echo "  ╚════════════════════════════════════════════╝"
echo -e "${NC}"

echo -e "  ${BOLD}EXE:${NC}  $EXE_NAME"
echo -e "  ${BOLD}Dir:${NC}  $EXE_DIR"
echo -e "  ${BOLD}Modo:${NC} $MODE"
echo ""

# Configurar ambiente base
export WINEPREFIX="${WINEPREFIX:-$HOME/.wine}"
export WINEFSYNC=1

# Configurar renderer
setup_environment() {
    case "$MODE" in
        opengl)
            echo -e "${BLUE}[RENDER]${NC} OpenGL por software (LLVMpipe)"
            export LIBGL_ALWAYS_SOFTWARE=1
            export GALLIUM_DRIVER=llvmpipe
            export LP_NUM_THREADS=${CORES:-0}
            export MESA_GL_VERSION_OVERRIDE=4.5
            export MESA_GLSL_VERSION_OVERRIDE=450
            ;;
        vulkan)
            echo -e "${BLUE}[RENDER]${NC} Vulkan por software (Lavapipe)"
            export LIBGL_ALWAYS_SOFTWARE=1
            VK_ICD=$(find /usr -name "lvp_icd*.json" 2>/dev/null | head -1)
            export VK_ICD_FILENAMES="${VK_ICD:-/usr/share/vulkan/icd.d/lvp_icd.x86_64.json}"
            export DRI_PRIME=0
            ;;
        full|*)
            echo -e "${BLUE}[RENDER]${NC} Renderização completa por software"
            export LIBGL_ALWAYS_SOFTWARE=1
            export GALLIUM_DRIVER=llvmpipe
            export LP_NUM_THREADS=${CORES:-0}
            export MESA_GL_VERSION_OVERRIDE=4.5
            export MESA_GLSL_VERSION_OVERRIDE=450
            export MESA_LOADER_DRIVER_OVERRIDE=zink
            VK_ICD=$(find /usr -name "lvp_icd*.json" 2>/dev/null | head -1)
            export VK_ICD_FILENAMES="${VK_ICD:-/usr/share/vulkan/icd.d/lvp_icd.x86_64.json}"
            export DRI_PRIME=0
            export __GLX_VENDOR_LIBRARY_NAME=mesa
            export MESA_NO_ERROR=1
            ;;
    esac
    
    # FPS limit
    if [ "$FPS_LIMIT" -gt 0 ]; then
        echo -e "${BLUE}[FPS]${NC} Limite: ${FPS_LIMIT}"
        export vblank_mode=1
        export __GL_SYNC_TO_VBLANK=1
    fi
    
    # Windowed
    if [ "$WINDOWED" -eq 1 ]; then
        EXTRA_ARGS+=("-windowed")
        echo -e "${BLUE}[VIDEO]${NC} Modo janela forçado"
    fi
    
    # Resolution
    if [ -n "$RESOLUTION" ]; then
        EXTRA_ARGS+=("-ResX=${RESOLUTION%x*}")
        EXTRA_ARGS+=("-ResY=${RESOLUTION#*x}")
        echo -e "${BLUE}[VIDEO]${NC} Resolução: $RESOLUTION"
    fi
    
    # Debug
    if [ "$DEBUG" -eq 1 ]; then
        export MESA_DEBUG=1
        export WINEDEBUG=+all
        echo -e "${YELLOW}[DEBUG]${NC} Modo debug ativado (logs detalhados)"
    fi
}

# Configurar afinidade de CPU
setup_affinity() {
    local total=$(nproc)
    local use_cores=$CORES
    
    if [ "$use_cores" -eq 0 ]; then
        # Auto: usar metade dos cores físicos
        use_cores=$((total / 2))
        [ "$use_cores" -lt 1 ] && use_cores=1
    fi
    
    local mask="0-$((use_cores - 1))"
    echo -e "${BLUE}[CPU]${NC} Afinidade: cores $mask (de $total threads)"
    
    # Retornar o comando de afinidade
    echo "taskset -c $mask"
}

echo -e "${BOLD}${CYAN}▶ Configurando ambiente...${NC}"
setup_environment

# Detectar se precisa de afinidade
AFFINITY_CMD=$(setup_affinity)

echo ""
echo -e "${BOLD}${GREEN}▶ Iniciando $EXE_NAME...${NC}"
echo -e "${YELLOW}Pressione Ctrl+C para encerrar${NC}"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Executar
if [ "$FPS_LIMIT" -gt 0 ] && command -v strangle &>/dev/null; then
    $AFFINITY_CMD strangle "$FPS_LIMIT" wine "$EXE_PATH" "${EXTRA_ARGS[@]}" || true
else
    $AFFINITY_CMD wine "$EXE_PATH" "${EXTRA_ARGS[@]}" || true
fi

echo ""
echo -e "${BOLD}${CYAN}$EXE_NAME encerrado.${NC}"
