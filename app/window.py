#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EMU-GPU Toolkit v2.0 - Janela Principal
Interface moderna com GTK4/libadwaita - estilo Steam/Lutris
"""

import os
import json
import subprocess
import threading
from pathlib import Path
from datetime import datetime

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib, Gio, Gdk

from core.config import (
    RENDERERS, COLORS, load_settings, save_settings,
    load_games, add_game, remove_game, TRANSLATION_MODULES,
    init_directories, HOME
)
from core.system import (
    get_cpu_info, get_ram_info, get_gpu_info,
    check_componentes, get_cpu_usage, get_ram_usage,
    set_game_mode, set_cpu_affinity
)
from core.translator import get_translator, TranslationLayer


class EmuGpuWindow(Adw.ApplicationWindow):
    """Janela principal do EMU-GPU Toolkit"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        self.set_title("EMU-GPU Toolkit")
        self.set_default_size(1200, 750)
        self.set_size_request(950, 600)
        
        # Estado
        self.settings = load_settings()
        self.translator = get_translator()
        self.current_page = "dashboard"
        self.selected_renderer = self.settings.get("default_renderer", "swrender-full")
        self.game_data = {}  # Dados do jogo sendo adicionado
        
        # Info do sistema
        self.cpu_info = get_cpu_info()
        self.ram_info = get_ram_info()
        self.gpu_info = get_gpu_info()
        self.comp_status = check_componentes()
        
        # Build UI
        self._build_ui()
        self._start_monitoring()
    
    def _build_ui(self):
        """Constrói a interface principal"""
        # Box principal
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(self.main_box)
        
        # Header Bar
        self._build_header()
        
        # Conteudo: Sidebar + Stack
        content_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.main_box.append(content_box)
        
        # Sidebar
        self._build_sidebar(content_box)
        
        # Stack de paginas
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self.stack.set_transition_duration(200)
        content_box.append(self.stack)
        
        # Paginas
        self._build_dashboard()
        self._build_library()
        self._build_add_game()
        self._build_settings()
        self._build_experimental()
        
        # Status bar
        self._build_status_bar()
        
        # Selecionar pagina inicial
        self._navigate_to("dashboard")
    
    def _build_header(self):
        """Header bar com estilo"""
        header = Adw.HeaderBar()
        header.add_css_class("flat")
        
        # Titulo
        title_widget = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        
        # Icone/Logo
        logo_label = Gtk.Label()
        logo_label.set_markup("<span font='16' weight='bold' color='#58a6ff'>EMU-GPU</span>")
        title_widget.append(logo_label)
        
        version_label = Gtk.Label()
        version_label.set_markup("<span font='10' color='#8b949e'>v2.0</span>")
        title_widget.append(version_label)
        
        header.set_title_widget(title_widget)
        
        # Botao de menu
        menu_button = Gtk.MenuButton()
        menu_button.set_icon_name("open-menu-symbolic")
        menu_button.set_tooltip_text("Menu")
        
        # Menu
        menu = Gio.Menu()
        menu.append("Sobre", "app.about")
        menu.append("Atualizar Tradutores", "app.update-translators")
        menu.append("Sair", "app.quit")
        
        menu_button.set_menu_model(menu)
        header.pack_end(menu_button)
        
        self.main_box.append(header)
    
    def _build_sidebar(self, parent):
        """Sidebar de navegacao estilo Steam"""
        sidebar_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        sidebar_box.set_size_request(220, -1)
        sidebar_box.add_css_class("sidebar")
        
        # Estilo do sidebar
        sidebar_box.set_margin_top(12)
        sidebar_box.set_margin_bottom(12)
        
        # Secao principal
        nav_items = [
            ("dashboard", "Dashboard", "dashboard-symbolic"),
            ("library", "Meus Jogos", "applications-games-symbolic"),
            ("add_game", "Adicionar Jogo", "list-add-symbolic"),
        ]
        
        for page_id, label, icon in nav_items:
            btn = Gtk.Button()
            btn.add_css_class("sidebar-button")
            btn.add_css_class("flat")
            
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            
            img = Gtk.Image.new_from_icon_name(icon)
            img.set_pixel_size(18)
            box.append(img)
            
            lbl = Gtk.Label(label=label)
            lbl.set_xalign(0)
            box.append(lbl)
            
            btn.set_child(box)
            btn.connect("clicked", lambda b, p=page_id: self._navigate_to(p))
            
            sidebar_box.append(btn)
            setattr(self, f"nav_{page_id}", btn)
        
        # Separador
        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        sep.set_margin_top(8)
        sep.set_margin_bottom(8)
        sep.set_margin_start(12)
        sep.set_margin_end(12)
        sidebar_box.append(sep)
        
        # Secao sistema
        sys_items = [
            ("settings", "Configuracoes", "preferences-system-symbolic"),
            ("experimental", "Experimental", "applications-science-symbolic"),
        ]
        
        for page_id, label, icon in sys_items:
            btn = Gtk.Button()
            btn.add_css_class("sidebar-button")
            btn.add_css_class("flat")
            
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            
            img = Gtk.Image.new_from_icon_name(icon)
            img.set_pixel_size(18)
            box.append(img)
            
            lbl = Gtk.Label(label=label)
            lbl.set_xalign(0)
            box.append(lbl)
            
            btn.set_child(box)
            btn.connect("clicked", lambda b, p=page_id: self._navigate_to(p))
            
            sidebar_box.append(btn)
            setattr(self, f"nav_{page_id}", btn)
        
        # Espacador
        sidebar_box.append(Gtk.Box())
        
        # Info do sistema no fundo
        info_frame = Gtk.Frame()
        info_frame.set_margin_start(12)
        info_frame.set_margin_end(12)
        info_frame.set_margin_bottom(8)
        
        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        info_box.set_margin_top(10)
        info_box.set_margin_bottom(10)
        info_box.set_margin_start(12)
        info_box.set_margin_end(12)
        
        # CPU
        self.status_cpu_label = Gtk.Label()
        self.status_cpu_label.set_xalign(0)
        self.status_cpu_label.set_markup(
            f"<span font='10' color='#8b949e'>CPU: </span>"
            f"<span font='10' color='#e6edf3'>{self.cpu_info['modelo'][:20]}...</span>"
        )
        info_box.append(self.status_cpu_label)
        
        # RAM
        self.status_ram_label = Gtk.Label()
        self.status_ram_label.set_xalign(0)
        self.status_ram_label.set_markup(
            f"<span font='10' color='#8b949e'>RAM: </span>"
            f"<span font='10' color='#e6edf3'>{self.ram_info['total_gb']} GB</span>"
        )
        info_box.append(self.status_ram_label)
        
        # GPU
        gpu_text = self.gpu_info['modelo'][:25] if len(self.gpu_info['modelo']) > 25 else self.gpu_info['modelo']
        gpu_label = Gtk.Label()
        gpu_label.set_xalign(0)
        gpu_label.set_markup(
            f"<span font='10' color='#8b949e'>GPU: </span>"
            f"<span font='10' color='#e6edf3'>{gpu_text}</span>"
        )
        info_box.append(gpu_label)
        
        info_frame.set_child(info_box)
        sidebar_box.append(info_frame)
        
        parent.append(sidebar_box)
    
    def _navigate_to(self, page_name):
        """Navega para uma pagina"""
        self.current_page = page_name
        self.stack.set_visible_child_name(page_name)
        
        # Atualizar estado dos botoes
        for p in ["dashboard", "library", "add_game", "settings", "experimental"]:
            btn = getattr(self, f"nav_{p}", None)
            if btn:
                if p == page_name:
                    btn.add_css_class("selected")
                else:
                    btn.remove_css_class("selected")
        
        # Refresh da pagina se necessario
        if page_name == "library":
            self._refresh_library()
        elif page_name == "dashboard":
            self._refresh_dashboard()
    
    # =================================================================
    # DASHBOARD
    # =================================================================
    def _build_dashboard(self):
        """Constrói a pagina do dashboard"""
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        box.set_margin_top(24)
        box.set_margin_bottom(24)
        box.set_margin_start(24)
        box.set_margin_end(24)
        scroll.set_child(box)
        
        # Titulo
        title = Gtk.Label()
        title.add_css_class("title-large")
        title.set_xalign(0)
        title.set_markup("Dashboard")
        box.append(title)
        
        subtitle = Gtk.Label()
        subtitle.set_xalign(0)
        subtitle.set_markup("<span color='#8b949e'>Visao geral do sistema e status dos componentes</span>")
        box.append(subtitle)
        
        # Grid de cards
        grid = Gtk.Grid()
        grid.set_column_spacing(16)
        grid.set_row_spacing(16)
        grid.set_margin_top(16)
        box.append(grid)
        
        # Card 1: Hardware
        hw_card = self._create_card("Hardware Detectado")
        hw_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        hw_content.set_margin_top(8)
        
        specs = [
            ("Processador", f"{self.cpu_info['modelo']} ({self.cpu_info['cores_fisicos']}C/{self.cpu_info['threads']}T)"),
            ("Frequencia Max", self.cpu_info['freq_max']),
            ("Memoria RAM", f"{self.ram_info['total_gb']} GB"),
            ("GPU", self.gpu_info['modelo']),
        ]
        
        for label, value in specs:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            lbl = Gtk.Label()
            lbl.set_xalign(0)
            lbl.set_markup(f"<span color='#8b949e'>{label}:</span>")
            lbl.set_size_request(120, -1)
            row.append(lbl)
            
            val = Gtk.Label()
            val.set_xalign(0)
            val.set_hexpand(True)
            val.set_markup(f"<span color='#e6edf3' font='10'>{value}</span>")
            val.set_wrap(True)
            row.append(val)
            
            hw_content.append(row)
        
        hw_card.set_child(hw_content)
        grid.attach(hw_card, 0, 0, 1, 1)
        
        # Card 2: Status Componentes
        status_card = self._create_card("Status dos Componentes")
        status_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        status_content.set_margin_top(8)
        
        components = [
            ("Vulkan", self.comp_status["vulkan"]),
            ("Mesa / LLVMpipe", self.comp_status["llvmpipe"]),
            ("Lavapipe", self.comp_status["lavapipe"]),
            ("Tradutor DXVK", self.comp_status["translators"].get("dxvk", False)),
            ("Tradutor VKD3D", self.comp_status["translators"].get("vkd3d", False)),
        ]
        
        for name, ok in components:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            
            lbl = Gtk.Label()
            lbl.set_xalign(0)
            lbl.set_hexpand(True)
            lbl.set_markup(f"<span color='#e6edf3'>{name}</span>")
            row.append(lbl)
            
            status = Gtk.Label()
            status.set_markup(
                f"<span color='{'#3fb950' if ok else '#f85149'}' font='11' weight='bold'>"
                f"{'ONLINE' if ok else 'OFFLINE'}"
                f"</span>"
            )
            row.append(status)
            
            status_content.append(row)
        
        status_card.set_child(status_content)
        grid.attach(status_card, 1, 0, 1, 1)
        
        # Card 3: Acoes Rapidas
        actions_card = self._create_card("Acoes Rapidas")
        actions_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        actions_content.set_margin_top(8)
        
        # Botao principal: Escolher e rodar
        btn_rodar = Gtk.Button()
        btn_rodar.add_css_class("accent-button")
        btn_rodar.set_label("ESCOLHER .EXE E RODAR")
        btn_rodar.connect("clicked", self._on_quick_run)
        actions_content.append(btn_rodar)
        
        # Botoes secundarios
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        btn_box.set_homogeneous(True)
        
        btn_jogos = Gtk.Button(label="Meus Jogos")
        btn_jogos.connect("clicked", lambda b: self._navigate_to("library"))
        btn_box.append(btn_jogos)
        
        btn_add = Gtk.Button(label="Adicionar Jogo")
        btn_add.connect("clicked", lambda b: self._navigate_to("add_game"))
        btn_box.append(btn_add)
        
        btn_config = Gtk.Button(label="Configuracoes")
        btn_config.connect("clicked", lambda b: self._navigate_to("settings"))
        btn_box.append(btn_config)
        
        actions_content.append(btn_box)
        
        # Dica
        dica = Gtk.Label()
        dica.set_xalign(0)
        dica.set_markup(
            "<span color='#d29922' font='10'>"
            "DICA: Para i7-2760QM, use 'Render Completo' com 30 FPS em 1280x720."
            "</span>"
        )
        dica.set_wrap(True)
        actions_content.append(dica)
        
        actions_card.set_child(actions_content)
        grid.attach(actions_card, 0, 1, 2, 1)
        
        self.stack.add_named(scroll, "dashboard")
        self.dashboard_grid = grid
    
    def _refresh_dashboard(self):
        """Atualiza dados do dashboard"""
        self.comp_status = check_componentes()
    
    # =================================================================
    # BIBLIOTECA
    # =================================================================
    def _build_library(self):
        """Constrói a pagina da biblioteca de jogos"""
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        box.set_margin_top(24)
        box.set_margin_bottom(24)
        box.set_margin_start(24)
        box.set_margin_end(24)
        scroll.set_child(box)
        
        # Header
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        
        title = Gtk.Label()
        title.add_css_class("title-large")
        title.set_xalign(0)
        title.set_hexpand(True)
        title.set_markup("Meus Jogos")
        header_box.append(title)
        
        btn_add = Gtk.Button(label="+ Adicionar Jogo")
        btn_add.connect("clicked", lambda b: self._navigate_to("add_game"))
        header_box.append(btn_add)
        
        btn_refresh = Gtk.Button()
        btn_refresh.set_icon_name("view-refresh-symbolic")
        btn_refresh.set_tooltip_text("Atualizar")
        btn_refresh.connect("clicked", lambda b: self._refresh_library())
        header_box.append(btn_refresh)
        
        box.append(header_box)
        
        # Container dos jogos
        self.games_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.append(self.games_container)
        
        self.stack.add_named(scroll, "library")
    
    def _refresh_library(self):
        """Atualiza a lista de jogos"""
        # Limpar container
        while True:
            child = self.games_container.get_first_child()
            if child is None:
                break
            self.games_container.remove(child)
        
        games = load_games()
        
        if not games:
            # Estado vazio
            empty_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
            empty_box.set_margin_top(80)
            empty_box.set_halign(Gtk.Align.CENTER)
            
            icon = Gtk.Image.new_from_icon_name("applications-games-symbolic")
            icon.set_pixel_size(64)
            icon.set_opacity(0.3)
            empty_box.append(icon)
            
            lbl = Gtk.Label()
            lbl.set_markup("<span font='16' color='#8b949e'>Nenhum jogo na biblioteca</span>")
            empty_box.append(lbl)
            
            btn = Gtk.Button(label="Adicionar meu primeiro jogo")
            btn.add_css_class("accent-button")
            btn.connect("clicked", lambda b: self._navigate_to("add_game"))
            empty_box.append(btn)
            
            self.games_container.append(empty_box)
            return
        
        # Grid de jogos
        games_grid = Gtk.Grid()
        games_grid.set_column_spacing(12)
        games_grid.set_row_spacing(12)
        games_grid.set_margin_top(8)
        
        col = 0
        row = 0
        for game in games:
            card = self._create_game_card(game)
            games_grid.attach(card, col, row, 1, 1)
            
            col += 1
            if col >= 2:
                col = 0
                row += 1
        
        self.games_container.append(games_grid)
    
    def _create_game_card(self, game):
        """Cria um card de jogo estilo Steam"""
        card = Gtk.Frame()
        card.add_css_class("game-card")
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        box.set_margin_start(16)
        box.set_margin_end(16)
        
        # Nome do jogo
        nome = game.get("nome", "Desconhecido")
        renderer_key = game.get("renderer", "swrender-full")
        renderer_info = RENDERERS.get(renderer_key, RENDERERS["swrender-full"])
        
        title = Gtk.Label()
        title.set_xalign(0)
        title.set_markup(f"<span font='14' weight='bold' color='#e6edf3'>{nome}</span>")
        title.set_ellipsize(3)  # Pango.EllipsizeMode.END
        box.append(title)
        
        # Caminho
        caminho = game.get("caminho", "")
        caminho_display = caminho if len(caminho) < 60 else "..." + caminho[-57:]
        path_lbl = Gtk.Label()
        path_lbl.set_xalign(0)
        path_lbl.set_markup(f"<span font='9' color='#6e7681'>{caminho_display}</span>")
        path_lbl.set_ellipsize(3)
        box.append(path_lbl)
        
        # Info row
        info_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        info_box.set_margin_top(4)
        
        renderer_badge = Gtk.Label()
        renderer_badge.set_markup(
            f"<span font='9' color='{renderer_info['cor']}' bgcolor='{renderer_info['cor_bg']}'> "
            f"  {renderer_info['subtitulo']}  "
            f"</span>"
        )
        info_box.append(renderer_badge)
        
        fps_lbl = Gtk.Label()
        fps_lbl.set_markup(f"<span font='9' color='#8b949e'>{game.get('fps_limit', 30)} FPS</span>")
        info_box.append(fps_lbl)
        
        res_lbl = Gtk.Label()
        res_lbl.set_markup(f"<span font='9' color='#8b949e'>{game.get('resolucao', '1280x720')}</span>")
        info_box.append(res_lbl)
        
        box.append(info_box)
        
        # Botoes
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        btn_box.set_margin_top(12)
        
        btn_play = Gtk.Button(label="JOGAR")
        btn_play.add_css_class("accent-button")
        btn_play.set_hexpand(True)
        btn_play.connect("clicked", lambda b, g=game: self._launch_game(g))
        btn_box.append(btn_play)
        
        btn_remove = GtkButtonWithIcon("user-trash-symbolic")
        btn_remove.set_tooltip_text("Remover")
        btn_remove.connect("clicked", lambda b, g=game: self._remove_game_confirm(g))
        btn_box.append(btn_remove)
        
        box.append(btn_box)
        
        card.set_child(box)
        return card
    
    def _launch_game(self, game):
        """Lanca um jogo"""
        threading.Thread(target=self._run_game_thread, args=(game,), daemon=True).start()
    
    def _run_game_thread(self, game):
        """Thread de execucao do jogo"""
        try:
            GLib.idle_add(self._show_toast, f"Iniciando {game.get('nome', 'jogo')}...")
            
            # Preparar ambiente
            env = self.translator.prepare_game_environment(game)
            
            # Executar o script de lancamento
            script_path = env["launcher_script"]
            
            GLib.idle_add(self._show_toast, f"{game.get('nome')} iniciado!")
            
            result = subprocess.run(
                ["/bin/bash", str(script_path)],
                capture_output=True,
                text=True,
                timeout=None
            )
            
        except Exception as e:
            GLib.idle_add(self._show_toast, f"Erro: {str(e)}")
    
    def _remove_game_confirm(self, game):
        """Confirma remocao do jogo"""
        dialog = Adw.MessageDialog(
            transient_for=self,
            heading="Remover Jogo",
            body=f"Deseja remover '{game.get('nome')}' da biblioteca?\n\nO arquivo original nao sera apagado."
        )
        dialog.add_response("cancel", "Cancelar")
        dialog.add_response("remove", "Remover")
        dialog.set_response_appearance("remove", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")
        
        dialog.connect("response", lambda d, response: (
            self._do_remove_game(game.get("id")) if response == "remove" else None
        ))
        
        dialog.present()
    
    def _do_remove_game(self, game_id):
        """Remove o jogo"""
        remove_game(game_id)
        self._show_toast("Jogo removido da biblioteca")
        self._refresh_library()
    
    # =================================================================
    # ADICIONAR JOGO
    # =================================================================
    def _build_add_game(self):
        """Constrói a pagina de adicionar jogo"""
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        box.set_margin_top(24)
        box.set_margin_bottom(24)
        box.set_margin_start(24)
        box.set_margin_end(24)
        scroll.set_child(box)
        
        # Titulo
        title = Gtk.Label()
        title.add_css_class("title-large")
        title.set_xalign(0)
        title.set_markup("Adicionar Jogo")
        box.append(title)
        
        subtitle = Gtk.Label()
        subtitle.set_xalign(0)
        subtitle.set_markup("<span color='#8b949e'>Adicione um jogo .exe a biblioteca</span>")
        box.append(subtitle)
        
        # Secao 1: Selecionar executavel
        sec1 = self._create_card("1. Selecione o executavel (.exe)")
        sec1_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        sec1_content.set_margin_top(8)
        
        # Usar file chooser nativo do sistema (Nautilus via portal)
        path_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        
        self.exe_path_entry = Gtk.Entry()
        self.exe_path_entry.set_placeholder_text("Caminho do executavel...")
        self.exe_path_entry.set_hexpand(True)
        path_box.append(self.exe_path_entry)
        
        btn_browse = Gtk.Button(label="Abrir Nautilus...")
        btn_browse.connect("clicked", self._on_browse_exe)
        path_box.append(btn_browse)
        
        btn_native = GtkButtonWithIcon("folder-open-symbolic")
        btn_native.set_tooltip_text("Selecionar arquivo (sistema)")
        btn_native.connect("clicked", self._on_native_filechooser)
        path_box.append(btn_native)
        
        sec1_content.append(path_box)
        
        # Dica
        dica = Gtk.Label()
        dica.set_xalign(0)
        dica.set_markup(
            "<span color='#6e7681' font='10'>"
            "Dica: Use 'Abrir Nautilus' para navegar pelo explorador de arquivos nativo do Ubuntu. "
            "Voce pode acessar todos os seus HDs e armazenamentos.\n"
            "Exemplo: /media/dragonscp/Seu HD/jogos/meu_jogo.exe"
            "</span>"
        )
        dica.set_wrap(True)
        sec1_content.append(dica)
        
        # Botao de escanear pasta
        scan_btn = Gtk.Button(label="+ Escanear pasta inteira por .exe")
        scan_btn.set_margin_top(8)
        scan_btn.connect("clicked", self._on_scan_folder)
        sec1_content.append(scan_btn)
        
        sec1.set_child(sec1_content)
        box.append(sec1)
        
        # Secao 2: Nome do jogo
        sec2 = self._create_card("2. Nome do Jogo")
        sec2_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        sec2_content.set_margin_top(8)
        
        self.game_name_entry = Gtk.Entry()
        self.game_name_entry.set_placeholder_text("Nome do jogo...")
        sec2_content.append(self.game_name_entry)
        
        sec2.set_child(sec2_content)
        box.append(sec2)
        
        # Secao 3: Perfil de Performance
        sec3 = self._create_card("3. Perfil de Performance")
        sec3_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        sec3_content.set_margin_top(8)
        
        # Grid de renderers
        renderer_grid = Gtk.Grid()
        renderer_grid.set_column_spacing(12)
        renderer_grid.set_row_spacing(12)
        renderer_grid.set_column_homogeneous(True)
        
        col = 0
        self.renderer_buttons = {}
        for key, info in RENDERERS.items():
            card = Gtk.Frame()
            card.add_css_class("renderer-card")
            
            card_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            card_box.set_margin_top(16)
            card_box.set_margin_bottom(16)
            card_box.set_margin_start(16)
            card_box.set_margin_end(16)
            
            # Icone
            icon = Gtk.Label()
            icon.set_markup(f"<span font='28' color='{info['cor']}'>{info['icone']}</span>")
            card_box.append(icon)
            
            # Nome
            nome = Gtk.Label()
            nome.set_markup(f"<span font='12' weight='bold' color='#e6edf3'>{info['nome']}</span>")
            card_box.append(nome)
            
            # Subtitulo
            sub = Gtk.Label()
            sub.set_markup(f"<span font='10' color='{info['cor']}'>{info['subtitulo']}</span>")
            card_box.append(sub)
            
            # Desc
            desc = Gtk.Label()
            desc.set_markup(f"<span font='9' color='#8b949e'>{info['desc']}</span>")
            desc.set_wrap(True)
            desc.set_max_width_chars(25)
            card_box.append(desc)
            
            # Categoria badge
            badge = Gtk.Label()
            badge.set_margin_top(4)
            badge.set_markup(
                f"<span font='8' color='{info['cor']}' bgcolor='{info['cor_bg']}'>  {info['categoria']}  </span>"
            )
            card_box.append(badge)
            
            card.set_child(card_box)
            
            # Click handler
            gesture = Gtk.GestureClick()
            gesture.connect("pressed", lambda g, n, x, y, k=key: self._select_renderer(k))
            card.add_controller(gesture)
            
            renderer_grid.attach(card, col, 0, 1, 1)
            self.renderer_buttons[key] = card
            
            col += 1
        
        sec3_content.append(renderer_grid)
        sec3.set_child(sec3_content)
        box.append(sec3)
        
        # Secao 4: Configuracoes
        sec4 = self._create_card("4. Configuracoes Adicionais")
        sec4_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        sec4_content.set_margin_top(8)
        
        # FPS
        fps_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        fps_lbl = Gtk.Label()
        fps_lbl.set_markup("<span color='#e6edf3'>Limite de FPS:</span>")
        fps_lbl.set_size_request(120, -1)
        fps_lbl.set_xalign(0)
        fps_box.append(fps_lbl)
        
        self.fps_adjustment = Gtk.Adjustment(value=30, lower=15, upper=60, step_increment=5)
        self.fps_scale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=self.fps_adjustment)
        self.fps_scale.set_hexpand(True)
        self.fps_scale.set_draw_value(True)
        fps_box.append(self.fps_scale)
        
        sec4_content.append(fps_box)
        
        # Resolucao
        res_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        res_lbl = Gtk.Label()
        res_lbl.set_markup("<span color='#e6edf3'>Resolucao:</span>")
        res_lbl.set_size_request(120, -1)
        res_lbl.set_xalign(0)
        res_box.append(res_lbl)
        
        self.res_combo = Gtk.DropDown()
        res_strings = Gtk.StringList()
        resolutions = ["640x480", "800x600", "1024x768", "1280x720", "1366x768", "1600x900", "1920x1080"]
        for r in resolutions:
            res_strings.append(r)
        self.res_combo.set_model(res_strings)
        self.res_combo.set_selected(3)  # 1280x720
        res_box.append(self.res_combo)
        
        sec4_content.append(res_box)
        
        # Janela
        self.window_check = Gtk.CheckButton(label="Modo Janela (recomendado para testar)")
        self.window_check.set_active(True)
        sec4_content.append(self.window_check)
        
        sec4.set_child(sec4_content)
        box.append(sec4)
        
        # Botao salvar
        save_btn = Gtk.Button(label="SALVAR E ADICIONAR A BIBLIOTECA")
        save_btn.add_css_class("accent-button")
        save_btn.set_margin_top(16)
        save_btn.connect("clicked", self._on_save_game)
        box.append(save_btn)
        
        self.stack.add_named(scroll, "add_game")
        
        # Selecionar renderer padrao
        self._select_renderer(self.selected_renderer)
    
    def _on_browse_exe(self, button):
        """Abre Nautilus para navegar pelos arquivos"""
        try:
            # Abre o Nautilus no diretorio padrao
            ultimo = self.settings.get("ultimo_diretorio", str(HOME))
            subprocess.Popen(["nautilus", ultimo], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Mostra um dialogo com instrucoes
            dialog = Adw.MessageDialog(
                transient_for=self,
                heading="Nautilus Aberto",
                body="O Nautilus (gerenciador de arquivos) foi aberto.\n\n"
                     "Navegue ate o seu jogo (.exe), copie o caminho completo "
                     "(Ctrl+C) e cole no campo de texto do EMU-GPU.\n\n"
                     "Voce pode acessar todos os seus HDs em /media/dragonscp/"
            )
            dialog.add_response("ok", "Entendi")
            dialog.present()
            
        except Exception as e:
            self._show_toast(f"Erro ao abrir Nautilus: {e}")
    
    def _on_native_filechooser(self, button):
        """Abre o file chooser nativo do GTK4 (usa portal/Nautilus automaticamente)"""
        dialog = Gtk.FileDialog()
        dialog.set_title("Selecione o executavel (.exe)")
        
        # Filtro para .exe
        filter_exe = Gtk.FileFilter()
        filter_exe.set_name("Executaveis Windows")
        filter_exe.add_pattern("*.exe")
        filter_exe.add_pattern("*.EXE")
        
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(filter_exe)
        dialog.set_filters(filters)
        
        # Diretorio inicial
        ultimo = self.settings.get("ultimo_diretorio", str(HOME))
        dialog.set_initial_folder(Gio.File.new_for_path(ultimo))
        
        dialog.open(self, None, self._on_filechooser_response)
    
    def _on_filechooser_response(self, dialog, result):
        """Callback do file chooser"""
        try:
            file = dialog.open_finish(result)
            if file:
                path = file.get_path()
                self.exe_path_entry.set_text(path)
                
                # Auto-detectar nome
                nome = Path(path).stem
                if not self.game_name_entry.get_text():
                    self.game_name_entry.set_text(nome)
                
                # Salvar ultimo diretorio
                self.settings["ultimo_diretorio"] = str(Path(path).parent)
                save_settings(self.settings)
                
                # Analisar dependencias
                self._analyze_exe(path)
        except Exception:
            pass  # Usuario cancelou
    
    def _analyze_exe(self, path):
        """Analisa o executavel para detectar dependencias"""
        deps = self.translator.scan_exe_dependencies(path)
        
        if deps.get("directx_version"):
            self._show_toast(
                f"Detectado: {deps['directx_version']} | "
                f"Tradutores recomendados: {', '.join(deps['recomendacoes'][:2])}"
            )
    
    def _on_scan_folder(self, button):
        """Escaneia uma pasta por executaveis"""
        dialog = Gtk.FileDialog()
        dialog.set_title("Selecione a pasta com os jogos")
        
        ultimo = self.settings.get("ultimo_diretorio", str(HOME))
        dialog.set_initial_folder(Gio.File.new_for_path(ultimo))
        
        dialog.select_folder(self, None, self._on_folder_selected)
    
    def _on_folder_selected(self, dialog, result):
        """Callback da selecao de pasta"""
        try:
            folder = dialog.select_folder_finish(result)
            if folder:
                path = folder.get_path()
                self._scan_for_exes(path)
        except Exception:
            pass
    
    def _scan_for_exes(self, folder_path):
        """Escaneia por executaveis na pasta"""
        exes = list(Path(folder_path).rglob("*.exe"))
        
        if not exes:
            self._show_toast("Nenhum .exe encontrado na pasta")
            return
        
        if len(exes) == 1:
            self.exe_path_entry.set_text(str(exes[0]))
            self.game_name_entry.set_text(exes[0].stem)
            self._show_toast(f"1 executavel encontrado: {exes[0].name}")
        else:
            self._show_exe_selector(exes)
    
    def _show_exe_selector(self, exes):
        """Mostra dialogo para selecionar multiplos executaveis"""
        dialog = Adw.MessageDialog(
            transient_for=self,
            heading=f"{len(exes)} executaveis encontrados",
            body="Selecione os jogos que deseja adicionar:"
        )
        
        # Conteudo com checkboxes
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        content.set_margin_top(12)
        content.set_margin_bottom(12)
        
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_size_request(-1, 300)
        
        list_box = Gtk.ListBox()
        list_box.set_selection_mode(Gtk.SelectionMode.NONE)
        
        self.exe_checkboxes = []
        for exe in sorted(exes):
            row = Gtk.ListBoxRow()
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            box.set_margin_start(12)
            box.set_margin_end(12)
            box.set_margin_top(8)
            box.set_margin_bottom(8)
            
            check = Gtk.CheckButton()
            check.set_active(True)
            box.append(check)
            
            lbl = Gtk.Label()
            lbl.set_xalign(0)
            lbl.set_hexpand(True)
            lbl.set_markup(f"<span color='#e6edf3' font='10'>{exe.name}</span>\n"
                          f"<span color='#6e7681' font='8'>{exe.parent}</span>")
            box.append(lbl)
            
            row.set_child(box)
            list_box.append(row)
            self.exe_checkboxes.append((check, exe))
        
        scroll.set_child(list_box)
        content.append(scroll)
        
        dialog.set_extra_child(content)
        dialog.add_response("cancel", "Cancelar")
        dialog.add_response("add", f"Adicionar Selecionados")
        dialog.set_response_appearance("add", Adw.ResponseAppearance.SUGGESTED)
        
        dialog.connect("response", self._on_multi_exe_response)
        dialog.present()
    
    def _on_multi_exe_response(self, dialog, response):
        """Processa a selecao multipla"""
        if response != "add":
            return
        
        added = 0
        for check, exe in self.exe_checkboxes:
            if check.get_active():
                game_data = {
                    "nome": exe.stem,
                    "caminho": str(exe),
                    "renderer": self.selected_renderer,
                    "fps_limit": int(self.fps_adjustment.get_value()),
                    "resolucao": self._get_selected_resolution(),
                    "janela": self.window_check.get_active(),
                }
                add_game(game_data)
                added += 1
        
        self._show_toast(f"{added} jogos adicionados!")
        self._navigate_to("library")
    
    def _select_renderer(self, key):
        """Seleciona um renderer"""
        self.selected_renderer = key
        
        for k, card in self.renderer_buttons.items():
            if k == key:
                card.add_css_class("renderer-card-selected")
                card.remove_css_class("renderer-card")
            else:
                card.add_css_class("renderer-card")
                card.remove_css_class("renderer-card-selected")
    
    def _get_selected_resolution(self):
        """Retorna a resolucao selecionada"""
        model = self.res_combo.get_model()
        selected = self.res_combo.get_selected()
        return model.get_string(selected)
    
    def _on_save_game(self, button):
        """Salva o jogo na biblioteca"""
        caminho = self.exe_path_entry.get_text().strip()
        nome = self.game_name_entry.get_text().strip()
        
        if not caminho:
            self._show_toast("Por favor, informe o caminho do executavel")
            return
        
        if not Path(caminho).exists():
            self._show_toast(f"Arquivo nao encontrado: {caminho}")
            return
        
        if not nome:
            self._show_toast("Por favor, informe um nome para o jogo")
            return
        
        game_data = {
            "nome": nome,
            "caminho": caminho,
            "renderer": self.selected_renderer,
            "fps_limit": int(self.fps_adjustment.get_value()),
            "resolucao": self._get_selected_resolution(),
            "janela": self.window_check.get_active(),
        }
        
        add_game(game_data)
        
        self._show_toast(f"'{nome}' adicionado a biblioteca!")
        
        # Limpar form
        self.exe_path_entry.set_text("")
        self.game_name_entry.set_text("")
        
        self._navigate_to("library")
    
    # =================================================================
    # CONFIGURACOES
    # =================================================================
    def _build_settings(self):
        """Constrói a pagina de configuracoes"""
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        box.set_margin_top(24)
        box.set_margin_bottom(24)
        box.set_margin_start(24)
        box.set_margin_end(24)
        scroll.set_child(box)
        
        # Titulo
        title = Gtk.Label()
        title.add_css_class("title-large")
        title.set_xalign(0)
        title.set_markup("Configuracoes")
        box.append(title)
        
        # Secao: Renderer padrao
        sec1 = self._create_card("Renderer Padrao")
        sec1_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        sec1_content.set_margin_top(8)
        
        self.def_renderer_group = None
        for key, info in RENDERERS.items():
            radio = Gtk.CheckButton(label=f"  {info['nome']} - {info['subtitulo']}")
            radio.set_active(key == self.settings.get("default_renderer", "swrender-full"))
            if self.def_renderer_group:
                radio.set_group(self.def_renderer_group)
            else:
                self.def_renderer_group = radio
            radio.connect("toggled", lambda b, k=key: self._set_default_renderer(k) if b.get_active() else None)
            sec1_content.append(radio)
        
        sec1.set_child(sec1_content)
        box.append(sec1)
        
        # Secao: Translators
        sec2 = self._create_card("Modulos de Traducao")
        sec2_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        sec2_content.set_margin_top(8)
        
        self.translator_checks = {}
        for mod_id, mod_info in TRANSLATION_MODULES.items():
            status = self.translator.status_modulos().get(mod_id, {})
            
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            
            check = Gtk.CheckButton(label=mod_info["nome"])
            check.set_active(mod_id in self.settings.get("translators_ativos", ["dxvk"]))
            check.set_hexpand(True)
            row.append(check)
            self.translator_checks[mod_id] = check
            
            status_lbl = Gtk.Label()
            installed = status.get("instalado", False)
            status_lbl.set_markup(
                f"<span color='{'#3fb950' if installed else '#f85149'}' font='9'>"
                f"{'Instalado' if installed else 'Nao instalado'}"
                f"</span>"
            )
            row.append(status_lbl)
            
            if not installed:
                btn_install = Gtk.Button(label="Instalar")
                btn_install.set_size_request(80, -1)
                btn_install.connect("clicked", lambda b, m=mod_id: self._install_translator(m))
                row.append(btn_install)
            
            sec2_content.append(row)
        
        sec2.set_child(sec2_content)
        box.append(sec2)
        
        # Secao: Otimizacao
        sec3 = self._create_card("Otimizacao de CPU")
        sec3_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        sec3_content.set_margin_top(8)
        
        self.game_mode_check = Gtk.CheckButton(label="Ativar Game Mode (coloca CPU em performance maxima)")
        self.game_mode_check.set_active(self.settings.get("game_mode", False))
        sec3_content.append(self.game_mode_check)
        
        self.affinity_check = Gtk.CheckButton(label="Usar Afinidade de CPU (isola cores para o jogo)")
        self.affinity_check.set_active(self.settings.get("cpu_affinity", True))
        sec3_content.append(self.affinity_check)
        
        sec3.set_child(sec3_content)
        box.append(sec3)
        
        # Botao salvar
        save_btn = Gtk.Button(label="SALVAR CONFIGURACOES")
        save_btn.add_css_class("accent-button")
        save_btn.set_margin_top(16)
        save_btn.connect("clicked", self._on_save_settings)
        box.append(save_btn)
        
        self.stack.add_named(scroll, "settings")
    
    def _set_default_renderer(self, key):
        """Define o renderer padrao"""
        self.settings["default_renderer"] = key
    
    def _install_translator(self, mod_id):
        """Instala um modulo de traducao"""
        self._show_toast(f"Instalando {TRANSLATION_MODULES[mod_id]['nome']}...")
        
        def install_thread():
            success, msg = self.translator.download_modulo(mod_id)
            GLib.idle_add(lambda: self._show_toast(msg))
            if success:
                GLib.idle_add(self._build_settings)  # Recriar pagina
        
        threading.Thread(target=install_thread, daemon=True).start()
    
    def _on_save_settings(self, button):
        """Salva as configuracoes"""
        # Collect translator selections
        ativos = []
        for mod_id, check in self.translator_checks.items():
            if check.get_active():
                ativos.append(mod_id)
        
        self.settings["translators_ativos"] = ativos
        self.settings["game_mode"] = self.game_mode_check.get_active()
        self.settings["cpu_affinity"] = self.affinity_check.get_active()
        
        save_settings(self.settings)
        self._show_toast("Configuracoes salvas!")
    
    # =================================================================
    # FERRAMENTAS EXPERIMENTAIS
    # =================================================================
    def _build_experimental(self):
        """Constrói a pagina de ferramentas experimentais"""
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        box.set_margin_top(24)
        box.set_margin_bottom(24)
        box.set_margin_start(24)
        box.set_margin_end(24)
        scroll.set_child(box)
        
        # Titulo
        title = Gtk.Label()
        title.add_css_class("title-large")
        title.set_xalign(0)
        title.set_markup("Ferramentas Experimentais")
        box.append(title)
        
        subtitle = Gtk.Label()
        subtitle.set_xalign(0)
        subtitle.set_markup("<span color='#8b949e'>Recursos avancados e em desenvolvimento</span>")
        box.append(subtitle)
        
        # FSR (FidelityFX Super Resolution)
        fsr_card = self._create_card("AMD FSR (FidelityFX Super Resolution)")
        fsr_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        fsr_content.set_margin_top(8)
        
        fsr_desc = Gtk.Label()
        fsr_desc.set_xalign(0)
        fsr_desc.set_markup(
            "<span color='#8b949e' font='10'>"
            "Upscaling de imagem para melhorar performance. Renderiza em resolucao menor "
            "e upscale com qualidade. Ideal para CPUs com renderizacao por software."
            "</span>"
        )
        fsr_desc.set_wrap(True)
        fsr_content.append(fsr_desc)
        
        self.fsr_check = Gtk.CheckButton(label="Ativar FSR (experimental)")
        self.fsr_check.set_active(self.settings.get("experimental_tools", {}).get("fsr", False))
        fsr_content.append(self.fsr_check)
        
        fsr_card.set_child(fsr_content)
        box.append(fsr_card)
        
        # Frame Generation
        fg_card = self._create_card("Frame Generation")
        fg_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        fg_content.set_margin_top(8)
        
        fg_desc = Gtk.Label()
        fg_desc.set_xalign(0)
        fg_desc.set_markup(
            "<span color='#8b949e' font='10'>"
            "Gera frames intermediarios para aumentar FPS. Usa processamento da CPU "
            "para criar frames adicionais entre os frames renderizados. "
            "Requer CPU potente (8+ threads recomendado)."
            "</span>"
        )
        fg_desc.set_wrap(True)
        fg_content.append(fg_desc)
        
        self.fg_check = Gtk.CheckButton(label="Ativar Frame Generation (muito experimental)")
        self.fg_check.set_active(self.settings.get("experimental_tools", {}).get("frame_gen", False))
        fg_content.append(self.fg_check)
        
        fg_card.set_child(fg_content)
        box.append(fg_card)
        
        # Shader Cache
        sc_card = self._create_card("Shader Cache")
        sc_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        sc_content.set_margin_top(8)
        
        sc_desc = Gtk.Label()
        sc_desc.set_xalign(0)
        sc_desc.set_markup(
            "<span color='#8b949e' font='10'>"
            "Cache de shaders compilados para reduzir stuttering. Compila shaders "
            "uma vez e reutiliza em execucoes futuras."
            "</span>"
        )
        sc_desc.set_wrap(True)
        sc_content.append(sc_desc)
        
        self.sc_check = Gtk.CheckButton(label="Ativar Shader Cache (recomendado)")
        self.sc_check.set_active(self.settings.get("experimental_tools", {}).get("shader_cache", True))
        sc_content.append(self.sc_check)
        
        # Botao limpar cache
        btn_clear = Gtk.Button(label="Limpar Cache de Shaders")
        btn_clear.set_margin_top(8)
        btn_clear.connect("clicked", self._on_clear_cache)
        sc_content.append(btn_clear)
        
        sc_card.set_child(sc_content)
        box.append(sc_card)
        
        # Info
        info = Gtk.Label()
        info.set_margin_top(16)
        info.set_markup(
            "<span color='#d29922' font='10'>"
            "Aviso: Estas ferramentas sao experimentais e podem causar instabilidade. "
            "Use por sua conta e risco."
            "</span>"
        )
        info.set_wrap(True)
        box.append(info)
        
        self.stack.add_named(scroll, "experimental")
    
    def _on_clear_cache(self, button):
        """Limpa o cache de shaders"""
        cache_dir = Path.home() / ".emu-gpu" / "cache" / "shaders"
        if cache_dir.exists():
            import shutil
            shutil.rmtree(cache_dir)
            cache_dir.mkdir(parents=True, exist_ok=True)
            self._show_toast("Cache de shaders limpo!")
        else:
            self._show_toast("Nenhum cache para limpar")
    
    # =================================================================
    # UTILITARIOS
    # =================================================================
    def _create_card(self, title):
        """Cria um card estilizado"""
        card = Gtk.Frame()
        card.add_css_class("card")
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.set_margin_top(16)
        box.set_margin_bottom(16)
        box.set_margin_start(16)
        box.set_margin_end(16)
        
        if title:
            lbl = Gtk.Label()
            lbl.set_xalign(0)
            lbl.set_markup(f"<span font='12' weight='bold' color='#e6edf3'>{title}</span>")
            box.append(lbl)
            
            sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
            sep.set_margin_top(8)
            sep.set_margin_bottom(8)
            box.append(sep)
        
        card.set_child(box)
        # Store content box for later use
        card._content = box
        
        return card
    
    def _show_toast(self, message):
        """Mostra uma mensagem toast"""
        # Use the root overlay or print for now
        print(f"[EMU-GPU] {message}")
    
    def _start_monitoring(self):
        """Inicia monitoramento do sistema"""
        pass  # Simplificado para esta versao


class GtkButtonWithIcon(Gtk.Button):
    """Botao com icone"""
    
    def __init__(self, icon_name):
        super().__init__()
        img = Gtk.Image.new_from_icon_name(icon_name)
        img.set_pixel_size(16)
        self.set_child(img)
