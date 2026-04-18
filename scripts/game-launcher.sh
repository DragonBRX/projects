#!/bin/bash
# =============================================================================
# EMU-GPU Game Launcher
# Script avançado para lançar jogos .exe com emulação GPU via CPU
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

# Diretórios
INSTALL_DIR="${EMU_GPU_TOOLKIT:-$HOME/.emu-gpu}"
CONFIG_DIR="$INSTALL_DIR/config"
GAMES_DIR="${EMU_GAMES_DIR:-$HOME/Games/exe-translated}"
WINE_PREFIX="${WINEPREFIX:-$HOME/.wine}"

# Configurações padrão
RENDERER="${EMU_RENDERER:-swrender-full}"
FPS_LIMIT="${EMU_FPS_LIMIT:-0}"
CPU_AFFINITY="${EMU_CPU_AFFINITY:-1}"
GAME_MODE="${EMU_GAME_MODE:-0}"
SHOW_HUD="${EMU_HUD:-0}"

# Variáveis de renderização por software
setup_swrender() {
    case "$RENDERER" in
        llvmpipe)
            export LIBGL_ALWAYS_SOFTWARE=1
            export GALLIUM_DRIVER=llvmpipe
            export LP_NUM_THREADS=0
            export MESA_GL_VERSION_OVERRIDE=4.5
            export MESA_GLSL_VERSION_OVERRIDE=450
            export MESA_NO_ERROR=1
            export __GL_THREADED_OPTIMIZATIONS=1
            echo -e "${BLUE}[GPU]${NC} Modo: LLVMpipe (OpenGL por CPU)"
            ;;
        lavapipe)
            export VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.x86_64.json
            if [ ! -f "$VK_ICD_FILENAMES" ]; then
                VK_ICD_FILENAMES=$(find /usr -name "lvp_icd*.json" 2>/dev/null | head -1)
                export VK_ICD_FILENAMES
            fi
            export DRI_PRIME=0
            export __GLX_VENDOR_LIBRARY_NAME=mesa
            echo -e "${BLUE}[GPU]${NC} Modo: Lavapipe (Vulkan por CPU)"
            ;;
        swrender-full|*)
            export LIBGL_ALWAYS_SOFTWARE=1
            export GALLIUM_DRIVER=llvmpipe
            export LP_NUM_THREADS=0
            export MESA_GL_VERSION_OVERRIDE=4.5
            export MESA_GLSL_VERSION_OVERRIDE=450
            export MESA_LOADER_DRIVER_OVERRIDE=zink
            export VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.x86_64.json
            if [ ! -f "$VK_ICD_FILENAMES" ]; then
                VK_ICD_FILENAMES=$(find /usr -name "lvp_icd*.json" 2>/dev/null | head -1)
                export VK_ICD_FILENAMES
            fi
            export DRI_PRIME=0
            export __GLX_VENDOR_LIBRARY_NAME=mesa
            export MESA_NO_ERROR=1
            export __GL_THREADED_OPTIMIZATIONS=1
            echo -e "${BLUE}[GPU]${NC} Modo: Software Render Full (OpenGL+Vulkan por CPU via Zink)"
            ;;
    esac
}

# Otimização de CPU
setup_cpu() {
    if [ "$GAME_MODE" == "1" ]; then
        echo -e "${BLUE}[CPU]${NC} Ativando Game Mode (performance)..."
        for cpu in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor 2>/dev/null; do
            echo performance > "$cpu" 2>/dev/null || true
        done
        echo 0 > /sys/devices/system/cpu/intel_pstate/no_turbo 2>/dev/null || true
    fi
    
    if [ "$CPU_AFFINITY" == "1" ]; then
        TOTAL=$(nproc)
        PHYSICAL=$((TOTAL / 2))
        if [ "$PHYSICAL" -lt 1 ]; then PHYSICAL=1; fi
        AFFINITY="0-$((PHYSICAL - 1))"
        CPU_AFFINITY_MASK="$AFFINITY"
        echo -e "${BLUE}[CPU]${NC} Afinidade: cores $AFFINITY"
    fi
}

# Limitador de FPS
setup_fps_limit() {
    if [ "$FPS_LIMIT" -gt 0 ]; then
        echo -e "${BLUE}[FPS]${NC} Limite: ${FPS_LIMIT} FPS"
        export __GL_SYNC_TO_VBLANK=1
        export vblank_mode=1
    fi
}

# HUD de performance
setup_hud() {
    if [ "$SHOW_HUD" == "1" ]; then
        if command -v mangohud &>/dev/null; then
            HUD_CMD="mangohud"
            echo -e "${BLUE}[HUD]${NC} MangoHud ativado"
        else
            echo -e "${YELLOW}[HUD]${NC} MangoHud não instalado (sudo apt install mangohud)"
            HUD_CMD=""
        fi
    fi
}

# Verificar se é jogo instalado
find_game() {
    local game_name="$1"
    
    # Verificar configuração de jogos
    CONFIG_FILE="$INSTALL_DIR/config/settings.json"
    if [ -f "$CONFIG_FILE" ]; then
        # Procurar no JSON (usando python)
        GAME_DIR=$(python3 -c "
import json
with open('$CONFIG_FILE') as f:
    config = json.load(f)
for game in config.get('installed_games', []):
    if game['name'].lower() == '$game_name'.lower():
        print(game['dir'])
        break
" 2>/dev/null)
        
        if [ -n "$GAME_DIR" ]; then
            echo "$GAME_DIR"
            return 0
        fi
    fi
    
    # Procurar no diretório de jogos
    if [ -d "$GAMES_DIR/$game_name" ]; then
        echo "$GAMES_DIR/$game_name"
        return 0
    fi
    
    return 1
}

# Encontrar executável principal no diretório do jogo
find_main_exe() {
    local game_dir="$1"
    local game_name="$2"
    
    # Procurar .exe no diretório
    local exes=($(find "$game_dir" -maxdepth 3 -name "*.exe" -type f 2>/dev/null))
    
    if [ ${#exes[@]} -eq 0 ]; then
        echo ""
        return 1
    fi
    
    # Se só houver um, retornar ele
    if [ ${#exes[@]} -eq 1 ]; then
        echo "${exes[0]}"
        return 0
    fi
    
    # Tentar encontrar o executável principal
    for exe in "${exes[@]}"; do
        local basename=$(basename "$exe" | tr '[:upper:]' '[:lower:]')
        # Priorizar launchers ou executáveis com nome do jogo
        if [[ "$basename" == *"launcher"* ]] || [[ "$basename" == *"start"* ]] || \
           [[ "$basename" == *"${game_name,,}"* ]] || [[ "$basename" == *"game"* ]]; then
            echo "$exe"
            return 0
        fi
    done
    
    # Retornar o primeiro (ou o maior arquivo)
    echo "${exes[0]}"
    return 0
}

# Banner
echo -e "${BOLD}${CYAN}"
echo "  ╔════════════════════════════════════════════╗"
echo "  ║      EMU-GPU Game Launcher v1.0            ║"
echo "  ║      GPU via CPU + Tradutor .exe           ║"
echo "  ╚════════════════════════════════════════════╝"
echo -e "${NC}"

# Parse argumentos
EXE_PATH=""
GAME_NAME=""
EXTRA_ARGS=()

while [[ $# -gt 0 ]]; do
    case $1 in
        --renderer|-r)
            RENDERER="$2"
            shift 2
            ;;
        --fps-limit|-f)
            FPS_LIMIT="$2"
            shift 2
            ;;
        --no-cpu-affinity)
            CPU_AFFINITY=0
            shift
            ;;
        --game-mode|-g)
            GAME_MODE=1
            shift
            ;;
        --hud|-h)
            SHOW_HUD=1
            shift
            ;;
        --wine-prefix)
            WINE_PREFIX="$2"
            shift 2
            ;;
        --help)
            echo "Uso: $0 [opções] <caminho-do-jogo.exe|nome-do-jogo> [args...]"
            echo ""
            echo "Opções:"
            echo "  --renderer <tipo>     Tipo de renderer (llvmpipe, lavapipe, swrender-full)"
            echo "  --fps-limit <n>       Limitar FPS"
            echo "  --no-cpu-affinity     Desabilitar afinidade de CPU"
            echo "  --game-mode, -g       Ativar game mode (CPU performance)"
            echo "  --hud, -h             Mostrar HUD de performance"
            echo "  --wine-prefix <path>  Prefixo Wine a usar"
            echo "  --help                Esta ajuda"
            echo ""
            echo "Exemplos:"
            echo "  $0 /caminho/para/jogo.exe"
            echo "  $0 --renderer llvmpipe --fps-limit 30 jogo.exe"
            echo "  $0 --game-mode --hud \"Nome do Jogo\""
            exit 0
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

# Verificar argumento
if [ -z "$EXE_PATH" ]; then
    echo -e "${RED}[ERRO]${NC} Especifique um executável ou nome de jogo"
    echo "Uso: $0 <caminho-do-jogo.exe|nome-do-jogo>"
    exit 1
fi

# Verificar se é um nome de jogo instalado ou caminho
if [ -f "$EXE_PATH" ]; then
    # É um caminho de arquivo
    FULL_EXE_PATH="$EXE_PATH"
    GAME_NAME=$(basename "$EXE_PATH" .exe)
elif [ -d "$GAMES_DIR/$EXE_PATH" ]; then
    # É um nome de jogo no diretório
    GAME_NAME="$EXE_PATH"
    GAME_DIR=$(find_game "$GAME_NAME")
    if [ -z "$GAME_DIR" ]; then
        GAME_DIR="$GAMES_DIR/$GAME_NAME"
    fi
    FULL_EXE_PATH=$(find_main_exe "$GAME_DIR" "$GAME_NAME")
    if [ -z "$FULL_EXE_PATH" ]; then
        echo -e "${RED}[ERRO]${NC} Nenhum .exe encontrado em $GAME_DIR"
        exit 1
    fi
    WINE_PREFIX="$GAME_DIR/wine_prefix"
else
    echo -e "${RED}[ERRO]${NC} Arquivo ou jogo não encontrado: $EXE_PATH"
    exit 1
fi

echo ""
echo -e "${BOLD}Jogo:${NC}    $GAME_NAME"
echo -e "${BOLD}EXE:${NC}     $FULL_EXE_PATH"
echo -e "${BOLD}Wine:${NC}    $WINE_PREFIX"
echo ""

# Configurar ambiente
echo -e "${BOLD}${CYAN}▶ Configurando ambiente...${NC}"
setup_swrender
setup_cpu
setup_fps_limit
setup_hud

# Exportar Wine prefix
export WINEPREFIX="$WINE_PREFIX"

# Construir comando
CMD=()

# Afinidade de CPU
if [ "$CPU_AFFINITY" == "1" ] && [ -n "$CPU_AFFINITY_MASK" ]; then
    CMD+=("taskset" "-c" "$CPU_AFFINITY_MASK")
fi

# HUD
if [ -n "$HUD_CMD" ]; then
    CMD+=("$HUD_CMD")
fi

# Wine + executável
CMD+=("wine" "$FULL_EXE_PATH")

# Argumentos extras
if [ ${#EXTRA_ARGS[@]} -gt 0 ]; then
    CMD+=("${EXTRA_ARGS[@]}")
fi

echo ""
echo -e "${BOLD}${GREEN}▶ Iniciando $GAME_NAME...${NC}"
echo -e "${BOLD}${GREEN}  Pressione Ctrl+C para encerrar${NC}"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Executar
if [ "$FPS_LIMIT" -gt 0 ] && command -v strangle &>/dev/null; then
    # Usar strangle para limitar FPS
    strangle "$FPS_LIMIT" "${CMD[@]}" || true
else
    "${CMD[@]}" || true
fi

echo ""
echo -e "${BOLD}${CYAN}$GAME_NAME encerrado.${NC}"
