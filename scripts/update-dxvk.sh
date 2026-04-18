#!/bin/bash
# =============================================================================
# EMU-GPU DXVK Updater
# Atualiza ou instala versões específicas do DXVK
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
DXVK_DIR="$INSTALL_DIR/dxvk"
WINE_PREFIX="${WINEPREFIX:-$HOME/.wine}"

show_help() {
    echo -e "${BOLD}${CYAN}EMU-GPU DXVK Updater${NC}"
    echo ""
    echo "Uso: $0 [opções]"
    echo ""
    echo "Opções:"
    echo "  --version VERSION   Instalar versão específica (ex: 1.10.3, 2.3.1)"
    echo "  --latest            Instalar última versão compatível"
    echo "  --stable            Instalar versão estável recomendada (padrão)"
    echo "  --prefix PATH       Prefixo Wine alvo"
    echo "  --list              Listar versões disponíveis"
    echo "  --help              Esta ajuda"
}

VERSION=""
MODE="stable"

while [[ $# -gt 0 ]]; do
    case $1 in
        --help|-h)
            show_help
            exit 0
            ;;
        --version|-v)
            VERSION="$2"
            shift 2
            ;;
        --latest)
            MODE="latest"
            shift
            ;;
        --stable)
            MODE="stable"
            shift
            ;;
        --prefix)
            WINE_PREFIX="$2"
            shift 2
            ;;
        --list)
            echo -e "${BOLD}${CYAN}Versões DXVK disponíveis:${NC}"
            echo ""
            echo "Estáveis (recomendadas para GPUs via software):"
            echo "  1.10.3  - Máxima compatibilidade, funciona com Lavapipe"
            echo "  1.10.4  - Compatibilidade boa"
            echo "  2.0     - Requer Vulkan 1.3"
            echo "  2.1     - Melhor performance em hardware real"
            echo "  2.2     - Features avançadas"
            echo "  2.3.1   - Última versão"
            echo ""
            exit 0
            ;;
        *)
            echo -e "${RED}Opção desconhecida: $1${NC}"
            show_help
            exit 1
            ;;
    esac
done

# Definir versão baseado no modo
case "$MODE" in
    stable)
        VERSION="${VERSION:-1.10.3}"
        ;;
    latest)
        VERSION="${VERSION:-2.3.1}"
        ;;
esac

echo -e "${BOLD}${CYAN}"
echo "  ╔════════════════════════════════════════════╗"
echo "  ║      EMU-GPU DXVK Updater                  ║"
echo "  ╚════════════════════════════════════════════╝"
echo -e "${NC}"

echo -e "  ${BOLD}Versão:${NC}  $VERSION"
echo -e "  ${BOLD}Prefixo:${NC} $WINE_PREFIX"
echo ""

mkdir -p "$DXVK_DIR"
cd "$DXVK_DIR"

# Baixar DXVK
ARCHIVE="dxvk-${VERSION}.tar.gz"
if [ ! -f "$ARCHIVE" ]; then
    echo -e "${BLUE}[DOWNLOAD]${NC} Baixando DXVK v${VERSION}..."
    URL="https://github.com/doitsujin/dxvk/releases/download/v${VERSION}/dxvk-${VERSION}.tar.gz"
    
    if ! wget -q --show-progress "$URL" -O "$ARCHIVE" 2>&1; then
        echo -e "${RED}[ERRO]${NC} Falha ao baixar DXVK ${VERSION}"
        echo -e "${YELLOW}Tentando versão alternativa...${NC}"
        
        # Fallback para versão mais antiga
        VERSION="1.10.3"
        ARCHIVE="dxvk-${VERSION}.tar.gz"
        URL="https://github.com/doitsujin/dxvk/releases/download/v${VERSION}/dxvk-${VERSION}.tar.gz"
        
        if ! wget -q --show-progress "$URL" -O "$ARCHIVE" 2>&1; then
            echo -e "${RED}[ERRO]${NC} Falha ao baixar versão alternativa"
            exit 1
        fi
    fi
else
    echo -e "${GREEN}[OK]${NC} Arquivo já existe: $ARCHIVE"
fi

# Extrair
echo -e "${BLUE}[EXTRACT]${NC} Extraindo..."
tar -xzf "$ARCHIVE"

DXVK_EXTRACTED="dxvk-${VERSION}"
if [ ! -d "$DXVK_EXTRACTED" ]; then
    echo -e "${RED}[ERRO]${NC} Diretório extraído não encontrado"
    exit 1
fi

echo -e "${GREEN}[OK]${NC} DXVK v${VERSION} extraído"

# Instalar no prefixo Wine
echo -e "${BLUE}[INSTALL]${NC} Instalando no prefixo Wine..."
export WINEPREFIX="$WINE_PREFIX"

# Copiar DLLs
if [ -d "$DXVK_EXTRACTED/x64" ]; then
    cp -v "$DXVK_EXTRACTED"/x64/*.dll "$WINE_PREFIX/drive_c/windows/system32/" 2>/dev/null || true
fi

if [ -d "$DXVK_EXTRACTED/x32" ]; then
    cp -v "$DXVK_EXTRACTED"/x32/*.dll "$WINE_PREFIX/drive_c/windows/syswow64/" 2>/dev/null || true
fi

# Configurar overrides no registro
echo -e "${BLUE}[CONFIG]${NC} Configurando overrides do Wine..."
wine reg add "HKCU\\Software\\Wine\\DllOverrides" /v d3d9 /d native /f >/dev/null 2>&1 || true
wine reg add "HKCU\\Software\\Wine\\DllOverrides" /v d3d10 /d native /f >/dev/null 2>&1 || true
wine reg add "HKCU\\Software\\Wine\\DllOverrides" /v d3d10_1 /d native /f >/dev/null 2>&1 || true
wine reg add "HKCU\\Software\\Wine\\DllOverrides" /v d3d10core /d native /f >/dev/null 2>&1 || true
wine reg add "HKCU\\Software\\Wine\\DllOverrides" /v d3d11 /d native /f >/dev/null 2>&1 || true
wine reg add "HKCU\\Software\\Wine\\DllOverrides" /v dxgi /d native /f >/dev/null 2>&1 || true

echo ""
echo -e "${GREEN}[✓] DXVK v${VERSION} instalado com sucesso!${NC}"
echo ""
echo -e "Para verificar: ${CYAN}vulkaninfo | grep -i device${NC}"
