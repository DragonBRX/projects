#!/bin/bash
# EMU-GPU Toolkit v2.0 - Launcher
# Inicia a interface grafica GTK4/libadwaita

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Verificar dependencias
check_dep() {
    if ! command -v "$1" &> /dev/null; then
        echo "[ERRO] $1 nao encontrado."
        return 1
    fi
    return 0
}

echo "EMU-GPU Toolkit v2.0"
echo "===================="

# Verificar Python3
if ! check_dep python3; then
    echo "Instale Python3: sudo apt install python3"
    exit 1
fi

# Verificar GTK4
if ! python3 -c "import gi; gi.require_version('Gtk', '4.0'); gi.require_version('Adw', '1')" 2>/dev/null; then
    echo "[AVISO] GTK4/libadwaita nao encontrado."
    echo "Instalando dependencias..."
    sudo apt install -y python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 libadwaita-1-0
fi

# Verificar Nautilus (explorador de arquivos)
if ! check_dep nautilus; then
    echo "[AVISO] Nautilus nao encontrado. Instalando..."
    sudo apt install -y nautilus
fi

cd "$SCRIPT_DIR"
python3 main.py "$@"
