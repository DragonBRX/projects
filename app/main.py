#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EMU-GPU Toolkit v2.0 - Entry Point
GPU via CPU + Traducao Propria de .exe para Ubuntu/Linux
"""

import sys
import signal
from pathlib import Path

# Verificar dependencias
try:
    import gi
    gi.require_version('Gtk', '4.0')
    gi.require_version('Adw', '1')
    from gi.repository import Gtk, Adw, GLib, Gio
except ImportError:
    print("=" * 60)
    print("DEPENDENCIAS NAO ENCONTRADAS")
    print("=" * 60)
    print("")
    print("O EMU-GPU Toolkit v2.0 requer GTK4 e libadwaita.")
    print("Instale com:")
    print("")
    print("  sudo apt install -y python3-gi gir1.2-gtk-4.0 gir1.2-adw-1")
    print("  sudo apt install -y libadwaita-1-0 zenity nautilus")
    print("")
    print("Ou use o install.sh que instala tudo automaticamente.")
    print("=" * 60)
    sys.exit(1)

from core.config import init_directories


class EmuGpuApplication(Adw.Application):
    """Aplicacao principal EMU-GPU Toolkit"""
    
    def __init__(self):
        super().__init__(
            application_id='com.dragonbrx.emugpu',
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS
        )
        
        self.set_resource_base_path('/com/dragonbrx/emugpu')
        
        # CSS Provider para estilos customizados
        self.css_provider = Gtk.CssProvider()
        
    def do_activate(self):
        """Ativa a aplicacao"""
        from window import EmuGpuWindow
        
        window = self.props.active_window
        if not window:
            window = EmuGpuWindow(application=self)
        
        window.present()
    
    def do_startup(self):
        """Inicializa a aplicacao"""
        Adw.Application.do_startup(self)
        
        # Inicializar diretorios
        init_directories()
        
        # Carregar CSS customizado
        self._load_styles()
    
    def _load_styles(self):
        """Carrega estilos CSS customizados"""
        css_data = """
        .game-card {
            background-color: #161b22;
            border-radius: 12px;
            border: 1px solid #30363d;
            padding: 16px;
            margin: 6px;
        }
        .game-card:hover {
            background-color: #1f2937;
            border-color: #58a6ff;
        }
        .renderer-card {
            background-color: #161b22;
            border-radius: 12px;
            border: 2px solid #30363d;
            padding: 20px;
        }
        .renderer-card-selected {
            background-color: #1f2937;
            border-color: #58a6ff;
        }
        .sidebar-button {
            padding: 12px 16px;
            border-radius: 8px;
            margin: 2px 8px;
        }
        .status-bar {
            background-color: #010409;
            padding: 8px 16px;
            font-size: 12px;
        }
        .title-large {
            font-size: 24px;
            font-weight: 800;
        }
        .accent-button {
            background-color: #238636;
            color: white;
            border-radius: 8px;
            padding: 10px 24px;
            font-weight: 700;
        }
        .accent-button:hover {
            background-color: #2ea043;
        }
        .card-grid {
            background-color: #0d1117;
        }
        """
        
        self.css_provider.load_from_data(css_data.encode(), -1)
        
        display = Gtk.Display.get_default()
        if display:
            Gtk.StyleContext.add_provider_for_display(
                display,
                self.css_provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )


def main():
    """Ponto de entrada principal"""
    # Handle SIGINT (Ctrl+C) graciosamente
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    
    app = EmuGpuApplication()
    return app.run(sys.argv)


if __name__ == '__main__':
    sys.exit(main())
