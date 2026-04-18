#!/bin/bash
# EMU-GPU Toolkit v2.1 - Launcher GUI
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "EMU-GPU Toolkit v2.1"
if ! python3 -c "import tkinter" 2>/dev/null; then
    echo "Instalando tkinter..."
    sudo apt install -y python3-tk
fi
python3 "$SCRIPT_DIR/emu_gpu_gui.py" "$@"
