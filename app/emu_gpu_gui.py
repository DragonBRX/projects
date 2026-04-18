#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =============================================================================
# EMU-GPU TOOLKIT v2.1 - Interface Grafica
# GPU via CPU + Tradutor de .exe para Ubuntu/Linux
# i7-2760QM + Intel HD 3000
# =============================================================================

import os
import sys
import json
import time
import threading
import subprocess
from pathlib import Path
from datetime import datetime

try:
    import tkinter as tk
    from tkinter import ttk, messagebox, filedialog, scrolledtext
except ImportError:
    print("tkinter nao encontrado. Instale: sudo apt install python3-tk")
    sys.exit(1)

VERSION = "2.1"
APP_NAME = "EMU-GPU Toolkit"
INSTALL_DIR = Path.home() / ".emu-gpu"
CONFIG_FILE = INSTALL_DIR / "config" / "settings.json"
GAMES_DIR = Path.home() / "Games" / "exe-translated"
WINE_PREFIX = Path.home() / ".wine"

COLORS = {
    "bg_dark": "#0d1117", "bg_card": "#161b22", "bg_hover": "#1f2937",
    "border": "#30363d", "text": "#e6edf3", "text_secondary": "#8b949e",
    "accent": "#58a6ff", "accent_hover": "#79b8ff", "success": "#3fb950",
    "warning": "#d29922", "danger": "#f85149", "purple": "#bc8cff",
    "cyan": "#39d0d8",
}

RENDERERS = {
    "llvmpipe": {
        "nome": "OpenGL por CPU (LLVMpipe)",
        "desc": "Melhor para jogos 2D e leves. Maxima compatibilidade.",
        "icone": "2D", "cor": "#3fb950", "fps_sug": 60,
        "env": {
            "LIBGL_ALWAYS_SOFTWARE": "1", "GALLIUM_DRIVER": "llvmpipe",
            "LP_NUM_THREADS": "0", "MESA_GL_VERSION_OVERRIDE": "4.5",
            "MESA_GLSL_VERSION_OVERRIDE": "450", "MESA_NO_ERROR": "1",
            "__GL_THREADED_OPTIMIZATIONS": "1",
        }
    },
    "lavapipe": {
        "nome": "Vulkan por CPU (Lavapipe)",
        "desc": "Para jogos com DXVK. DirectX 9/10/11 via Vulkan.",
        "icone": "3D", "cor": "#bc8cff", "fps_sug": 30,
        "env": {
            "VK_ICD_FILENAMES": "/usr/share/vulkan/icd.d/lvp_icd.x86_64.json",
            "LIBGL_ALWAYS_SOFTWARE": "1", "DRI_PRIME": "0",
            "__GLX_VENDOR_LIBRARY_NAME": "mesa",
        }
    },
    "swrender-full": {
        "nome": "Render Completo (Recomendado)",
        "desc": "OpenGL + Vulkan + Zink. Melhor resultado geral.",
        "icone": "MAX", "cor": "#58a6ff", "fps_sug": 30,
        "env": {
            "LIBGL_ALWAYS_SOFTWARE": "1", "GALLIUM_DRIVER": "llvmpipe",
            "LP_NUM_THREADS": "0", "MESA_GL_VERSION_OVERRIDE": "4.5",
            "MESA_GLSL_VERSION_OVERRIDE": "450", "MESA_LOADER_DRIVER_OVERRIDE": "zink",
            "VK_ICD_FILENAMES": "/usr/share/vulkan/icd.d/lvp_icd.x86_64.json",
            "DRI_PRIME": "0", "__GLX_VENDOR_LIBRARY_NAME": "mesa",
            "MESA_NO_ERROR": "1", "__GL_THREADED_OPTIMIZATIONS": "1",
        }
    },
}


def carregar_config():
    default = {
        "default_renderer": "swrender-full", "fps_limit": 30,
        "resolucao": "1280x720", "cpu_affinity": True,
        "game_mode": False, "janela": True, "jogos": [],
        "ultimo_diretorio": str(Path.home() / "Downloads"),
    }
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r') as f:
                default.update(json.load(f))
        except:
            pass
    return default


def salvar_config(cfg):
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, 'w') as f:
        json.dump(cfg, f, indent=2)


def obter_info_sistema():
    info = {"cpu": "Desconhecido", "nucleos": 0, "threads": 0, "ram_gb": 0, "gpu": "Desconhecido"}
    try:
        with open('/proc/cpuinfo', 'r') as f:
            content = f.read()
            for line in content.split('\n'):
                if 'model name' in line and info["cpu"] == "Desconhecido":
                    info["cpu"] = line.split(':')[1].strip()
            info["threads"] = content.count('processor')
        info["nucleos"] = info["threads"] // 2 if info["threads"] > 1 else info["threads"]
    except:
        pass
    try:
        with open('/proc/meminfo', 'r') as f:
            mem_kb = int(f.readline().split()[1])
            info["ram_gb"] = mem_kb // 1048576
    except:
        pass
    try:
        result = subprocess.run(['lspci'], capture_output=True, text=True, timeout=5)
        for line in result.stdout.split('\n'):
            if 'vga' in line.lower() or '3d' in line.lower() or 'display' in line.lower():
                info["gpu"] = line.split(':')[-1].strip()
                break
    except:
        pass
    return info


def verificar_wine():
    try:
        result = subprocess.run(['wine', '--version'], capture_output=True, text=True, timeout=5)
        return result.returncode == 0, result.stdout.strip()
    except:
        return False, "Nao instalado"


def verificar_vulkan():
    try:
        result = subprocess.run(['vulkaninfo', '--summary'], capture_output=True, text=True, timeout=5)
        return 'deviceName' in result.stdout
    except:
        return False


def encontrar_icd_vulkan():
    padrao = "/usr/share/vulkan/icd.d/lvp_icd.x86_64.json"
    if os.path.exists(padrao):
        return padrao
    try:
        result = subprocess.run(['find', '/usr', '-name', 'lvp_icd*.json'],
                              capture_output=True, text=True, timeout=5)
        if result.stdout.strip():
            return result.stdout.strip().split('\n')[0]
    except:
        pass
    return None


# =============================================================================
# APP PRINCIPAL
# =============================================================================

class EmuGPUApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"{APP_NAME} v{VERSION}")
        self.root.geometry("920x640")
        self.root.configure(bg=COLORS["bg_dark"])
        self.root.minsize(800, 550)

        self.config = carregar_config()
        self.info_sys = obter_info_sistema()
        self.wine_ok, self.wine_ver = verificar_wine()
        self.vulkan_ok = verificar_vulkan()
        self.icd_path = encontrar_icd_vulkan()

        self._configurar_estilo()
        self._criar_sidebar()
        self._criar_conteudo()
        self.mostrar_dashboard()
        self._atualizar_status()

    def _configurar_estilo(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Dark.TFrame", background=COLORS["bg_dark"])
        style.configure("Card.TFrame", background=COLORS["bg_card"])
        style.configure("Dark.TLabel", background=COLORS["bg_dark"], foreground=COLORS["text"])
        style.configure("TNotebook", background=COLORS["bg_dark"], borderwidth=0)
        style.configure("TNotebook.Tab", background=COLORS["bg_card"], foreground=COLORS["text"],
                       padding=(15, 8), font=("Segoe UI", 10))
        style.map("TNotebook.Tab",
                  background=[("selected", COLORS["accent"]), ("active", COLORS["bg_hover"])],
                  foreground=[("selected", "#ffffff")])

    def _criar_sidebar(self):
        self.sidebar = tk.Frame(self.root, bg=COLORS["bg_card"], width=200)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)

        logo_frame = tk.Frame(self.sidebar, bg=COLORS["bg_card"], height=70)
        logo_frame.pack(fill=tk.X, pady=(15, 10))
        logo_frame.pack_propagate(False)

        tk.Label(logo_frame, text="EMU-GPU", font=("Segoe UI", 18, "bold"),
                bg=COLORS["bg_card"], fg=COLORS["accent"]).pack(anchor="w", padx=20, pady=(5, 0))
        tk.Label(logo_frame, text=f"v{VERSION}", font=("Segoe UI", 9),
                bg=COLORS["bg_card"], fg=COLORS["text_secondary"]).pack(anchor="w", padx=20)

        tk.Frame(self.sidebar, bg=COLORS["border"], height=1).pack(fill=tk.X, padx=15, pady=5)

        botoes = [
            ("Dashboard", self.mostrar_dashboard),
            ("Meus Jogos", self.mostrar_jogos),
            ("Adicionar Jogo", self.mostrar_adicionar),
            ("Configuracoes", self.mostrar_config),
            ("Ajuda", self.mostrar_ajuda),
        ]

        self.btn_nav = {}
        for texto, comando in botoes:
            btn = tk.Button(self.sidebar, text=texto, font=("Segoe UI", 11),
                          bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                          activebackground=COLORS["bg_hover"], activeforeground=COLORS["text"],
                          bd=0, cursor="hand2", anchor="w", padx=20,
                          command=lambda c=comando, t=texto: self._nav(c, t))
            btn.pack(fill=tk.X, pady=2, ipady=8)
            self.btn_nav[texto] = btn

        tk.Frame(self.sidebar, bg=COLORS["border"], height=1).pack(fill=tk.X, padx=15, pady=10)

        self.lbl_status_cpu = tk.Label(self.sidebar, text="CPU: --", font=("Segoe UI", 9),
                                       bg=COLORS["bg_card"], fg=COLORS["text_secondary"])
        self.lbl_status_cpu.pack(anchor="w", padx=20, pady=2)
        self.lbl_status_ram = tk.Label(self.sidebar, text="RAM: --", font=("Segoe UI", 9),
                                       bg=COLORS["bg_card"], fg=COLORS["text_secondary"])
        self.lbl_status_ram.pack(anchor="w", padx=20, pady=2)

        tk.Label(self.sidebar, text=f"i7-2760QM | {self.info_sys['threads']}T",
                font=("Segoe UI", 8), bg=COLORS["bg_card"],
                fg=COLORS["text_secondary"]).pack(side=tk.BOTTOM, pady=15)

    def _criar_conteudo(self):
        self.main_frame = tk.Frame(self.root, bg=COLORS["bg_dark"])
        self.main_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=20, pady=20)

        self.header = tk.Frame(self.main_frame, bg=COLORS["bg_dark"])
        self.header.pack(fill=tk.X, pady=(0, 15))

        self.lbl_titulo = tk.Label(self.header, text="Dashboard", font=("Segoe UI", 22, "bold"),
                                   bg=COLORS["bg_dark"], fg=COLORS["text"])
        self.lbl_titulo.pack(side=tk.LEFT)

        self.lbl_subtitulo = tk.Label(self.header, text="", font=("Segoe UI", 11),
                                      bg=COLORS["bg_dark"], fg=COLORS["text_secondary"])
        self.lbl_subtitulo.pack(side=tk.LEFT, padx=(10, 0), pady=(8, 0))

        self.content = tk.Frame(self.main_frame, bg=COLORS["bg_dark"])
        self.content.pack(fill=tk.BOTH, expand=True)

    def _nav(self, comando, nome):
        for texto, btn in self.btn_nav.items():
            if texto == nome:
                btn.config(bg=COLORS["bg_hover"], fg=COLORS["text"])
            else:
                btn.config(bg=COLORS["bg_card"], fg=COLORS["text_secondary"])
        comando()

    def _limpar_conteudo(self):
        for widget in self.content.winfo_children():
            widget.destroy()

    def _criar_card(self, parent, titulo=None):
        card = tk.Frame(parent, bg=COLORS["bg_card"], highlightbackground=COLORS["border"],
                       highlightthickness=1, bd=0)
        if titulo:
            tk.Label(card, text=titulo, font=("Segoe UI", 12, "bold"),
                    bg=COLORS["bg_card"], fg=COLORS["text"]).pack(anchor="w", padx=15, pady=(12, 8))
            tk.Frame(card, bg=COLORS["border"], height=1).pack(fill=tk.X, padx=15, pady=(0, 8))
        return card

    # =====================================================================
    # DASHBOARD
    # =====================================================================

    def mostrar_dashboard(self):
        self._limpar_conteudo()
        self.lbl_titulo.config(text="Dashboard")
        self.lbl_subtitulo.config(text="Visao geral do sistema e status")

        grid = tk.Frame(self.content, bg=COLORS["bg_dark"])
        grid.pack(fill=tk.BOTH, expand=True)
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)
        grid.rowconfigure(1, weight=1)

        # Card Hardware
        card_hw = self._criar_card(grid, "Hardware Detectado")
        card_hw.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=(0, 8))
        info_texto = (
            f"Processador: {self.info_sys['cpu']}\n"
            f"Nucleos: {self.info_sys['nucleos']} fisicos / {self.info_sys['threads']} threads\n"
            f"Memoria RAM: {self.info_sys['ram_gb']} GB\n"
            f"GPU: {self.info_sys['gpu']}\n"
        )
        tk.Label(card_hw, text=info_texto, font=("Consolas", 10),
                bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                justify=tk.LEFT).pack(anchor="w", padx=15, pady=5)

        # Card Status
        card_status = self._criar_card(grid, "Status dos Componentes")
        card_status.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=(0, 8))

        status_itens = [
            ("Wine (tradutor .exe)", self.wine_ok, self.wine_ver if self.wine_ok else "Nao instalado"),
            ("Vulkan (API grafica)", self.vulkan_ok, "Disponivel" if self.vulkan_ok else "Nao instalado"),
            ("ICD Lavapipe", self.icd_path is not None, "Encontrado" if self.icd_path else "Nao encontrado"),
        ]
        for nome, ok, detalhe in status_itens:
            frame = tk.Frame(card_status, bg=COLORS["bg_card"])
            frame.pack(fill=tk.X, padx=15, pady=4)
            cor = COLORS["success"] if ok else COLORS["danger"]
            simbolo = "ON" if ok else "OFF"
            tk.Label(frame, text=nome, font=("Segoe UI", 10),
                    bg=COLORS["bg_card"], fg=COLORS["text"]).pack(side=tk.LEFT)
            tk.Label(frame, text=f"[{simbolo}]", font=("Consolas", 9, "bold"),
                    bg=COLORS["bg_card"], fg=cor).pack(side=tk.RIGHT)
            tk.Label(card_status, text=f"   {detalhe}", font=("Segoe UI", 9),
                    bg=COLORS["bg_card"], fg=COLORS["text_secondary"]).pack(anchor="w", padx=15)

        # Card Acoes
        card_acoes = self._criar_card(grid, "Acoes Rapidas")
        card_acoes.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(8, 0))

        acoes_frame = tk.Frame(card_acoes, bg=COLORS["bg_card"])
        acoes_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)

        btn_rodar = tk.Button(acoes_frame, text="ESCOLHER .EXE E RODAR",
                             font=("Segoe UI", 11, "bold"), bg=COLORS["accent"], fg="white",
                             activebackground=COLORS["accent_hover"], bd=0, cursor="hand2",
                             command=self._escolher_e_rodar)
        btn_rodar.pack(fill=tk.X, pady=(0, 8))

        btn_frame = tk.Frame(acoes_frame, bg=COLORS["bg_card"])
        btn_frame.pack(fill=tk.X)
        btn_frame.columnconfigure(0, weight=1)
        btn_frame.columnconfigure(1, weight=1)
        btn_frame.columnconfigure(2, weight=1)

        tk.Button(btn_frame, text="Meus Jogos", font=("Segoe UI", 10),
                 bg=COLORS["bg_hover"], fg=COLORS["text"], bd=0, cursor="hand2", pady=8,
                 command=self.mostrar_jogos).grid(row=0, column=0, sticky="ew", padx=(0, 4))
        tk.Button(btn_frame, text="Adicionar Jogo", font=("Segoe UI", 10),
                 bg=COLORS["bg_hover"], fg=COLORS["text"], bd=0, cursor="hand2", pady=8,
                 command=self.mostrar_adicionar).grid(row=0, column=1, sticky="ew", padx=4)
        tk.Button(btn_frame, text="Configuracoes", font=("Segoe UI", 10),
                 bg=COLORS["bg_hover"], fg=COLORS["text"], bd=0, cursor="hand2", pady=8,
                 command=self.mostrar_config).grid(row=0, column=2, sticky="ew", padx=(4, 0))

        tk.Label(card_acoes,
                text="DICA: Para i7-2760QM, use 'Render Completo' com 30 FPS em 720p.",
                font=("Segoe UI", 9), bg=COLORS["bg_card"],
                fg=COLORS["warning"], wraplength=750).pack(anchor="w", padx=15, pady=(5, 12))

    # =====================================================================
    # ADICIONAR JOGO - COM CAMPO DE TEXTO EDITAVEL
    # =====================================================================

    def mostrar_adicionar(self):
        self._limpar_conteudo()
        self.lbl_titulo.config(text="Adicionar Jogo")
        self.lbl_subtitulo.config(text="Adicione um jogo .exe a biblioteca")

        # Variaveis
        self.var_nome = tk.StringVar()
        self.var_renderer = tk.StringVar(value=self.config.get("default_renderer", "swrender-full"))
        self.var_fps = tk.IntVar(value=self.config.get("fps_limit", 30))
        self.var_res = tk.StringVar(value=self.config.get("resolucao", "1280x720"))
        self.var_janela = tk.BooleanVar(value=self.config.get("janela", True))

        # Canvas scrollavel
        canvas = tk.Canvas(self.content, bg=COLORS["bg_dark"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.content, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg=COLORS["bg_dark"])

        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw", width=660)
        canvas.configure(yscrollcommand=scrollbar.set)

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # ===== SECAO 1: CAMINHO DO .EXE (EDITAVEL + BOTAO PROCURAR) =====
        sec1 = self._criar_card(scroll_frame, "1. Caminho do executavel (.exe)")
        sec1.pack(fill=tk.X, pady=(0, 10))

        # Frame do campo de texto + botao
        path_frame = tk.Frame(sec1, bg=COLORS["bg_card"])
        path_frame.pack(fill=tk.X, padx=15, pady=(10, 5))

        # Campo de texto editavel - AQUI EH O CAMPO PARA COLAR O CAMINHO
        self.ent_caminho = tk.Entry(path_frame, font=("Consolas", 10),
                                    bg=COLORS["bg_hover"], fg=COLORS["text"],
                                    bd=1, relief=tk.FLAT, insertbackground=COLORS["accent"],
                                    insertwidth=2)
        self.ent_caminho.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=8, padx=(0, 8))
        self.ent_caminho.insert(0, "/media/dragonscp/")
        self.ent_caminho.bind("<KeyRelease>", self._auto_detectar_nome)

        tk.Button(path_frame, text="Procurar...", font=("Segoe UI", 10),
                 bg=COLORS["accent"], fg="white", bd=0, cursor="hand2",
                 padx=15, pady=5, command=self._procurar_exe_dialog).pack(side=tk.LEFT)

        # Label de dica
        tk.Label(sec1,
                text="DICA: Cole o caminho completo aqui (Ctrl+V) ou clique em 'Procurar...'\n"
                     "Exemplo: /media/dragonscp/Novo volume/jogos/meu_jogo.exe",
                font=("Segoe UI", 9), bg=COLORS["bg_card"],
                fg=COLORS["text_secondary"], justify=tk.LEFT).pack(anchor="w", padx=15, pady=(0, 10))

        # Botao de pegar jogos de uma pasta inteira
        pasta_frame = tk.Frame(sec1, bg=COLORS["bg_card"])
        pasta_frame.pack(fill=tk.X, padx=15, pady=(0, 10))
        tk.Button(pasta_frame, text="+ Procurar todos os .exe numa pasta",
                 font=("Segoe UI", 10), bg=COLORS["bg_hover"], fg=COLORS["accent"],
                 bd=0, cursor="hand2", padx=15, pady=6,
                 command=self._escanear_pasta).pack(side=tk.LEFT)

        # ===== SECAO 2: NOME =====
        sec2 = self._criar_card(scroll_frame, "2. Nome do Jogo")
        sec2.pack(fill=tk.X, pady=(0, 10))

        tk.Entry(sec2, textvariable=self.var_nome, font=("Segoe UI", 12),
                bg=COLORS["bg_hover"], fg=COLORS["text"], bd=1, relief=tk.FLAT,
                insertbackground=COLORS["accent"]).pack(fill=tk.X, padx=15, pady=10, ipady=6)

        # ===== SECAO 3: PERFIL =====
        sec3 = self._criar_card(scroll_frame, "3. Perfil de Performance")
        sec3.pack(fill=tk.X, pady=(0, 10))

        perfil_frame = tk.Frame(sec3, bg=COLORS["bg_card"])
        perfil_frame.pack(fill=tk.X, padx=15, pady=10)

        self.perfil_cards = {}
        for key, info in RENDERERS.items():
            pf = tk.Frame(perfil_frame, bg=COLORS["bg_hover"], bd=1, relief=tk.SOLID,
                         highlightbackground=COLORS["border"])
            pf.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4, ipady=10)

            tk.Label(pf, text=info["icone"], font=("Segoe UI", 20, "bold"),
                    bg=COLORS["bg_hover"], fg=info["cor"]).pack(pady=(5, 2))
            tk.Label(pf, text=info["nome"], font=("Segoe UI", 10, "bold"),
                    bg=COLORS["bg_hover"], fg=COLORS["text"],
                    wraplength=170, justify=tk.CENTER).pack(padx=5)
            tk.Label(pf, text=info["desc"], font=("Segoe UI", 9),
                    bg=COLORS["bg_hover"], fg=COLORS["text_secondary"],
                    wraplength=170, justify=tk.CENTER).pack(padx=5, pady=(2, 5))

            pf.bind("<Button-1>", lambda e, k=key: self._selecionar_renderer(k))
            for child in pf.winfo_children():
                child.bind("<Button-1>", lambda e, k=key: self._selecionar_renderer(k))
            self.perfil_cards[key] = pf

        self._selecionar_renderer(self.var_renderer.get())

        # ===== SECAO 4: CONFIGS =====
        sec4 = self._criar_card(scroll_frame, "4. Configuracoes Adicionais")
        sec4.pack(fill=tk.X, pady=(0, 10))

        cfg_frame = tk.Frame(sec4, bg=COLORS["bg_card"])
        cfg_frame.pack(fill=tk.X, padx=15, pady=10)

        tk.Label(cfg_frame, text="Limite de FPS:", font=("Segoe UI", 10),
                bg=COLORS["bg_card"], fg=COLORS["text"]).grid(row=0, column=0, sticky="w", pady=5)
        fps_frame = tk.Frame(cfg_frame, bg=COLORS["bg_card"])
        fps_frame.grid(row=0, column=1, sticky="w", padx=(10, 0), pady=5)
        tk.Scale(fps_frame, from_=15, to=60, orient=tk.HORIZONTAL,
                variable=self.var_fps, length=200, showvalue=True,
                bg=COLORS["bg_card"], fg=COLORS["accent"],
                troughcolor=COLORS["bg_hover"], highlightthickness=0).pack(side=tk.LEFT)

        tk.Label(cfg_frame, text="Resolucao:", font=("Segoe UI", 10),
                bg=COLORS["bg_card"], fg=COLORS["text"]).grid(row=1, column=0, sticky="w", pady=5)
        res_combo = ttk.Combobox(cfg_frame, textvariable=self.var_res,
                                 values=["640x480", "800x600", "1024x768", "1280x720",
                                        "1366x768", "1600x900", "1920x1080"],
                                 state="readonly", width=15)
        res_combo.grid(row=1, column=1, sticky="w", padx=(10, 0), pady=5)

        tk.Checkbutton(cfg_frame, text="Modo Janela (recomendado para testar)",
                      variable=self.var_janela, font=("Segoe UI", 10),
                      bg=COLORS["bg_card"], fg=COLORS["text"],
                      selectcolor=COLORS["bg_hover"], activebackground=COLORS["bg_card"],
                      activeforeground=COLORS["text"]).grid(row=2, column=0, columnspan=2,
                                                              sticky="w", pady=5)

        # ===== BOTAO SALVAR =====
        tk.Button(scroll_frame, text="SALVAR E ADICIONAR A BIBLIOTECA",
                 font=("Segoe UI", 13, "bold"), bg=COLORS["success"], fg="white",
                 activebackground=COLORS["success"], bd=0, cursor="hand2",
                 padx=30, pady=12, command=self._salvar_jogo).pack(pady=(15, 0))

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def _auto_detectar_nome(self, event=None):
        """Detecta nome automaticamente quando digita/cola o caminho"""
        caminho = self.ent_caminho.get().strip()
        if caminho and not self.var_nome.get():
            nome = Path(caminho).stem
            if nome:
                self.var_nome.set(nome)

    def _procurar_exe_dialog(self):
        """Abre dialogo de arquivo nativo"""
        inicial = self.config.get("ultimo_diretorio", str(Path.home()))
        caminho = filedialog.askopenfilename(
            title="Selecione o executavel",
            initialdir=inicial,
            filetypes=[("Executaveis Windows", "*.exe"), ("Todos", "*.*")]
        )
        if caminho:
            self.ent_caminho.delete(0, tk.END)
            self.ent_caminho.insert(0, caminho)
            nome = Path(caminho).stem
            if not self.var_nome.get():
                self.var_nome.set(nome)
            self.config["ultimo_diretorio"] = str(Path(caminho).parent)

    def _escanear_pasta(self):
        """Escanear uma pasta inteira procurando .exe"""
        inicial = self.config.get("ultimo_diretorio", str(Path.home()))
        pasta = filedialog.askdirectory(title="Selecione a pasta com os jogos",
                                        initialdir=inicial)
        if not pasta:
            return

        exes = list(Path(pasta).rglob("*.exe"))
        if not exes:
            messagebox.showinfo("Nenhum jogo encontrado",
                               f"Nenhum arquivo .exe encontrado em:\n{pasta}")
            return

        # Perguntar quais adicionar
        if len(exes) == 1:
            # Apenas um, adiciona direto
            self.ent_caminho.delete(0, tk.END)
            self.ent_caminho.insert(0, str(exes[0]))
            self.var_nome.set(exes[0].stem)
            messagebox.showinfo("Encontrado", f"1 executavel encontrado:\n{exes[0].name}")
        else:
            # Multiplos - mostrar janela de selecao
            self._mostrar_seletor_multiplos(exes)

    def _mostrar_seletor_multiplos(self, exes):
        """Mostra janela para selecionar multiplos .exe"""
        janela = tk.Toplevel(self.root)
        janela.title(f"{len(exes)} jogos encontrados")
        janela.geometry("500x400")
        janela.configure(bg=COLORS["bg_dark"])
        janela.transient(self.root)
        janela.grab_set()

        tk.Label(janela, text=f"{len(exes)} executaveis encontrados:",
                font=("Segoe UI", 12, "bold"), bg=COLORS["bg_dark"],
                fg=COLORS["text"]).pack(anchor="w", padx=15, pady=10)

        # Lista com checkboxes
        list_frame = tk.Frame(janela, bg=COLORS["bg_dark"])
        list_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)

        canvas = tk.Canvas(list_frame, bg=COLORS["bg_dark"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas, bg=COLORS["bg_dark"])
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw", width=450)
        canvas.configure(yscrollcommand=scrollbar.set)

        check_vars = []
        for exe in sorted(exes):
            var = tk.BooleanVar(value=True)
            check_vars.append((var, exe))
            cb = tk.Checkbutton(inner, text=f"{exe.name}\n   {exe.parent}",
                               variable=var, font=("Consolas", 9),
                               bg=COLORS["bg_dark"], fg=COLORS["text"],
                               selectcolor=COLORS["bg_hover"], activebackground=COLORS["bg_dark"],
                               wraplength=400, justify=tk.LEFT)
            cb.pack(anchor="w", pady=2)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        def adicionar_selecionados():
            adicionados = 0
            for var, exe in check_vars:
                if var.get():
                    jogo = {
                        "nome": exe.stem,
                        "caminho": str(exe),
                        "renderer": self.var_renderer.get(),
                        "fps_limit": self.var_fps.get(),
                        "resolucao": self.var_res.get(),
                        "janela": self.var_janela.get(),
                        "adicionado": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    }
                    self.config["jogos"] = [j for j in self.config["jogos"] if j["nome"] != jogo["nome"]]
                    self.config["jogos"].append(jogo)
                    adicionados += 1
            salvar_config(self.config)
            janela.destroy()
            messagebox.showinfo("Sucesso", f"{adicionados} jogos adicionados!")
            self.mostrar_jogos()

        btn_frame = tk.Frame(janela, bg=COLORS["bg_dark"])
        btn_frame.pack(fill=tk.X, padx=15, pady=10)
        tk.Button(btn_frame, text="Adicionar Selecionados", font=("Segoe UI", 11, "bold"),
                 bg=COLORS["success"], fg="white", bd=0, cursor="hand2",
                 padx=20, pady=8, command=adicionar_selecionados).pack(side=tk.LEFT)
        tk.Button(btn_frame, text="Cancelar", font=("Segoe UI", 11),
                 bg=COLORS["bg_hover"], fg=COLORS["text"], bd=0, cursor="hand2",
                 padx=20, pady=8, command=janela.destroy).pack(side=tk.RIGHT)

    def _selecionar_renderer(self, key):
        self.var_renderer.set(key)
        for k, frame in self.perfil_cards.items():
            if k == key:
                frame.config(highlightbackground=COLORS["accent"], highlightthickness=2)
            else:
                frame.config(highlightbackground=COLORS["border"], highlightthickness=1)

    def _salvar_jogo(self):
        caminho = self.ent_caminho.get().strip()
        nome = self.var_nome.get().strip()

        if not caminho:
            messagebox.showerror("Erro", "Digite ou cole o caminho do .exe!")
            return
        if not os.path.exists(caminho):
            messagebox.showerror("Erro", f"Arquivo nao encontrado:\n{caminho}\n\n"
                                          "Verifique se o caminho esta correto.\n"
                                          "Dica: Caminhos com espaco precisam estar completos.")
            return
        if not nome:
            messagebox.showerror("Erro", "Digite um nome para o jogo!")
            return

        jogo = {
            "nome": nome, "caminho": caminho,
            "renderer": self.var_renderer.get(),
            "fps_limit": self.var_fps.get(),
            "resolucao": self.var_res.get(),
            "janela": self.var_janela.get(),
            "adicionado": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
        self.config["jogos"] = [j for j in self.config["jogos"] if j["nome"] != nome]
        self.config["jogos"].append(jogo)
        salvar_config(self.config)
        messagebox.showinfo("Sucesso", f"'{nome}' adicionado a biblioteca!")
        self.mostrar_jogos()

    # =====================================================================
    # MEUS JOGOS
    # =====================================================================

    def mostrar_jogos(self):
        self._limpar_conteudo()
        self.lbl_titulo.config(text="Meus Jogos")
        self.lbl_subtitulo.config(text="Biblioteca de jogos e aplicativos")

        toolbar = tk.Frame(self.content, bg=COLORS["bg_dark"])
        toolbar.pack(fill=tk.X, pady=(0, 10))
        tk.Button(toolbar, text="+ Adicionar Jogo", font=("Segoe UI", 10, "bold"),
                 bg=COLORS["accent"], fg="white", bd=0, cursor="hand2",
                 padx=15, pady=6, command=self.mostrar_adicionar).pack(side=tk.LEFT)
        tk.Button(toolbar, text="Atualizar Lista", font=("Segoe UI", 10),
                 bg=COLORS["bg_hover"], fg=COLORS["text"], bd=0, cursor="hand2",
                 padx=15, pady=6, command=self.mostrar_jogos).pack(side=tk.LEFT, padx=(8, 0))

        if not self.config.get("jogos"):
            frame_vazio = tk.Frame(self.content, bg=COLORS["bg_dark"])
            frame_vazio.pack(expand=True)
            tk.Label(frame_vazio, text="Nenhum jogo adicionado ainda",
                    font=("Segoe UI", 16), bg=COLORS["bg_dark"],
                    fg=COLORS["text_secondary"]).pack(pady=(80, 10))
            tk.Button(frame_vazio, text="Adicionar meu primeiro jogo",
                     font=("Segoe UI", 12), bg=COLORS["accent"], fg="white",
                     bd=0, cursor="hand2", padx=25, pady=12,
                     command=self.mostrar_adicionar).pack(pady=10)
            return

        canvas = tk.Canvas(self.content, bg=COLORS["bg_dark"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.content, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg=COLORS["bg_dark"])
        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw", width=660)
        canvas.configure(yscrollcommand=scrollbar.set)

        for jogo in self.config["jogos"]:
            self._criar_card_jogo(scroll_frame, jogo)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def _criar_card_jogo(self, parent, jogo):
        card = tk.Frame(parent, bg=COLORS["bg_card"], highlightbackground=COLORS["border"],
                       highlightthickness=1, bd=0)
        card.pack(fill=tk.X, pady=4, ipady=8)

        nome = jogo.get("nome", "Desconhecido")
        caminho = jogo.get("caminho", "")
        renderer = jogo.get("renderer", "swrender-full")
        renderer_info = RENDERERS.get(renderer, RENDERERS["swrender-full"])

        tk.Label(card, text=nome, font=("Segoe UI", 13, "bold"),
                bg=COLORS["bg_card"], fg=COLORS["text"]).pack(anchor="w", padx=15)

        # Caminho com truncamento visual
        caminho_display = caminho if len(caminho) < 70 else "..." + caminho[-67:]
        tk.Label(card, text=f"Caminho: {caminho_display}", font=("Segoe UI", 9),
                bg=COLORS["bg_card"], fg=COLORS["text_secondary"]).pack(anchor="w", padx=15)

        btn_frame = tk.Frame(card, bg=COLORS["bg_card"])
        btn_frame.pack(anchor="w", padx=15, pady=(8, 0))

        tk.Button(btn_frame, text="JOGAR", font=("Segoe UI", 10, "bold"),
                 bg=COLORS["success"], fg="white", bd=0, cursor="hand2",
                 padx=20, pady=5,
                 command=lambda j=jogo: self._rodar_jogo(j)).pack(side=tk.LEFT)

        tk.Label(btn_frame, text=f"  {renderer_info['nome']}", font=("Segoe UI", 9),
                bg=COLORS["bg_card"], fg=renderer_info["cor"]).pack(side=tk.LEFT, padx=(10, 0))

        tk.Button(btn_frame, text="Remover", font=("Segoe UI", 9),
                 bg=COLORS["bg_card"], fg=COLORS["danger"], bd=0,
                 cursor="hand2", padx=10,
                 command=lambda j=nome: self._remover_jogo(j)).pack(side=tk.RIGHT)

    def _remover_jogo(self, nome):
        if messagebox.askyesno("Confirmar", f"Remover '{nome}' da biblioteca?"):
            self.config["jogos"] = [j for j in self.config["jogos"] if j["nome"] != nome]
            salvar_config(self.config)
            self.mostrar_jogos()

    # =====================================================================
    # CONFIGURACOES
    # =====================================================================

    def mostrar_config(self):
        self._limpar_conteudo()
        self.lbl_titulo.config(text="Configuracoes")
        self.lbl_subtitulo.config(text="Ajustes globais do toolkit")

        form = tk.Frame(self.content, bg=COLORS["bg_dark"])
        form.pack(fill=tk.BOTH, expand=True)

        sec1 = self._criar_card(form, "Renderer Padrao")
        sec1.pack(fill=tk.X, pady=(0, 10))
        var_def_renderer = tk.StringVar(value=self.config.get("default_renderer", "swrender-full"))
        for key, info in RENDERERS.items():
            tk.Radiobutton(sec1, text=f"  {info['nome']}", variable=var_def_renderer,
                          value=key, font=("Segoe UI", 11), bg=COLORS["bg_card"],
                          fg=COLORS["text"], selectcolor=COLORS["bg_hover"],
                          activebackground=COLORS["bg_card"]).pack(anchor="w", padx=15, pady=4)

        sec2 = self._criar_card(form, "FPS Limite Padrao")
        sec2.pack(fill=tk.X, pady=(0, 10))
        var_def_fps = tk.IntVar(value=self.config.get("fps_limit", 30))
        tk.Scale(sec2, from_=15, to=60, orient=tk.HORIZONTAL, variable=var_def_fps,
                length=300, showvalue=True, bg=COLORS["bg_card"], fg=COLORS["accent"],
                troughcolor=COLORS["bg_hover"], highlightthickness=0).pack(padx=15, pady=10)
        tk.Label(sec2, text="Recomendado: 30 FPS para jogos 3D, 60 FPS para jogos 2D",
                font=("Segoe UI", 9), bg=COLORS["bg_card"],
                fg=COLORS["text_secondary"]).pack(padx=15, pady=(0, 10))

        sec3 = self._criar_card(form, "Resolucao Padrao")
        sec3.pack(fill=tk.X, pady=(0, 10))
        var_def_res = tk.StringVar(value=self.config.get("resolucao", "1280x720"))
        ttk.Combobox(sec3, textvariable=var_def_res,
                    values=["640x480", "800x600", "1024x768", "1280x720",
                           "1366x768", "1600x900", "1920x1080"],
                    state="readonly", width=20).pack(padx=15, pady=10)
        tk.Label(sec3, text="Dica: 1280x720 e o ideal para o i7-2760QM",
                font=("Segoe UI", 9), bg=COLORS["bg_card"],
                fg=COLORS["warning"]).pack(padx=15, pady=(0, 10))

        sec4 = self._criar_card(form, "Otimizacao de CPU")
        sec4.pack(fill=tk.X, pady=(0, 10))
        var_game_mode = tk.BooleanVar(value=self.config.get("game_mode", False))
        tk.Checkbutton(sec4, text="Ativar Game Mode (coloca CPU em performance maxima)",
                      variable=var_game_mode, font=("Segoe UI", 11), bg=COLORS["bg_card"],
                      fg=COLORS["text"], selectcolor=COLORS["bg_hover"]).pack(anchor="w", padx=15, pady=8)
        var_affinity = tk.BooleanVar(value=self.config.get("cpu_affinity", True))
        tk.Checkbutton(sec4, text="Usar Afinidade de CPU (isola cores para o jogo)",
                      variable=var_affinity, font=("Segoe UI", 11), bg=COLORS["bg_card"],
                      fg=COLORS["text"], selectcolor=COLORS["bg_hover"]).pack(anchor="w", padx=15, pady=8)

        def salvar_tudo():
            self.config["default_renderer"] = var_def_renderer.get()
            self.config["fps_limit"] = var_def_fps.get()
            self.config["resolucao"] = var_def_res.get()
            self.config["game_mode"] = var_game_mode.get()
            self.config["cpu_affinity"] = var_affinity.get()
            salvar_config(self.config)
            messagebox.showinfo("Salvo", "Configuracoes salvas com sucesso!")

        tk.Button(form, text="SALVAR CONFIGURACOES", font=("Segoe UI", 12, "bold"),
                 bg=COLORS["accent"], fg="white", bd=0, cursor="hand2",
                 padx=25, pady=10, command=salvar_tudo).pack(pady=(15, 0))

    # =====================================================================
    # AJUDA
    # =====================================================================

    def mostrar_ajuda(self):
        self._limpar_conteudo()
        self.lbl_titulo.config(text="Ajuda")
        self.lbl_subtitulo.config(text="Como usar o EMU-GPU Toolkit")

        texto = scrolledtext.ScrolledText(self.content, wrap=tk.WORD, font=("Segoe UI", 11),
                                         bg=COLORS["bg_dark"], fg=COLORS["text"], bd=0,
                                         highlightthickness=0, insertbackground=COLORS["text"])
        texto.pack(fill=tk.BOTH, expand=True)
        texto.insert(tk.END, """EMU-GPU Toolkit v2.1 - Ajuda

O QUE E ISTO?
O EMU-GPU Toolkit transforma sua CPU em uma placa de video virtual usando
tecnologias de renderizacao por software. Ideal para quem tem CPU potente
mas GPU fraca (como Intel HD 3000).

COMO ADICIONAR UM JOGO:
1. Clique em "Adicionar Jogo" na barra lateral
2. No campo de caminho, COLE (Ctrl+V) ou DIGITE o caminho completo:
   Exemplo: /media/dragonscp/Novo volume/jogos/meu_jogo.exe
   Ou clique em "Procurar..." para navegar pelas pastas
3. Escolha um nome para o jogo
4. Selecione o perfil de performance:
   - OpenGL por CPU: jogos 2D e leves
   - Vulkan por CPU: jogos que usam DXVK
   - Render Completo: melhor resultado geral (RECOMENDADO)
5. Ajuste o limite de FPS (30 para 3D, 60 para 2D)
6. Escolha a resolucao (1280x720 e o ideal)
7. Clique em "SALVAR E ADICIONAR"

PARA JOGAR:
1. Va em "Meus Jogos"
2. Clique no botao VERDE "JOGAR" ao lado do jogo
3. O jogo abrira automaticamente

ADICIONAR JOGOS DE OUTRO HD/PENDRIVE:
1. Em "Adicionar Jogo", use o campo de texto para colar o caminho
2. O caminho comeca com /media/dragonscp/ (seu nome de usuario)
3. Exemplo: /media/dragonscp/Novo volume/jogos/game.exe
4. Voce tambem pode clicar em "Procurar todos os .exe numa pasta"
   e selecionar uma pasta inteira — o app acha todos os jogos!

DICAS DE PERFORMANCE:
- SEMPRE use limite de FPS (30 para jogos 3D)
- Jogue em 1280x720, nao em 1080p
- Use "Render Completo" como padrao
- Feche navegador e programas antes de jogar
- Ative "Game Mode" nas configuracoes

JOGOS QUE DEVEM RODAR:
Stardew Valley, Terraria, Hollow Knight, Celeste, Minecraft (OptiFine),
Portal 1/2, Half-Life 2, GTA San Andreas, Fallout 3/NV, Skyrim (2011)

ERROS COMUNS:
- "Arquivo nao encontrado": Verifique se o caminho esta correto
- "Jogo muito lento": Diminua resolucao e FPS
- "Tela preta": Tente outro renderer nas configuracoes do jogo
""")
        texto.config(state=tk.DISABLED)

    # =====================================================================
    # EXECUTAR JOGO
    # =====================================================================

    def _escolher_e_rodar(self):
        caminho = filedialog.askopenfilename(
            title="Selecione o executavel (.exe)",
            initialdir=self.config.get("ultimo_diretorio", str(Path.home())),
            filetypes=[("Executaveis Windows", "*.exe"), ("Todos", "*.*")]
        )
        if not caminho:
            return

        perfil = messagebox.askyesnocancel(
            "Perfil de Performance",
            "Escolha o perfil:\n\n"
            "SIM = Render Completo (Recomendado - jogos 3D)\n"
            "NAO = OpenGL por CPU (jogos 2D/leves)\n"
            "CANCELAR = Vulkan por CPU (especifico DXVK)"
        )
        renderer = "swrender-full" if perfil is True else "llvmpipe" if perfil is False else "lavapipe"

        self._rodar_jogo({
            "nome": Path(caminho).stem, "caminho": caminho,
            "renderer": renderer, "fps_limit": self.config.get("fps_limit", 30),
            "resolucao": self.config.get("resolucao", "1280x720"),
            "janela": self.config.get("janela", True),
        })

    def _rodar_jogo(self, jogo):
        caminho = jogo.get("caminho", "")
        renderer_key = jogo.get("renderer", "swrender-full")
        fps_limit = jogo.get("fps_limit", 30)
        resolucao = jogo.get("resolucao", "1280x720")
        janela = jogo.get("janela", True)

        if not Path(caminho).exists():
            messagebox.showerror("Erro", f"Arquivo nao encontrado:\n{caminho}")
            return

        renderer = RENDERERS.get(renderer_key, RENDERERS["swrender-full"])
        env = os.environ.copy()
        env.update(renderer["env"])

        if "VK_ICD_FILENAMES" in env:
            icd = env["VK_ICD_FILENAMES"]
            if not os.path.exists(icd) and self.icd_path:
                env["VK_ICD_FILENAMES"] = self.icd_path

        env["WINEPREFIX"] = str(WINE_PREFIX)

        if fps_limit > 0:
            env["__GL_SYNC_TO_VBLANK"] = "1"
            env["vblank_mode"] = "1"

        cmd = []
        if self.config.get("cpu_affinity", True):
            total = os.cpu_count() or 4
            physical = max(total // 2, 1)
            cmd.extend(["taskset", "-c", f"0-{physical - 1}"])

        cmd.extend(["wine", caminho])

        if janela:
            cmd.append("-windowed")

        if resolucao and "x" in resolucao:
            w, h = resolucao.split("x")
            cmd.extend([f"-ResX={w}", f"-ResY={h}"])

        print(f"[EMU-GPU] Iniciando: {jogo.get('nome', 'jogo')}")
        print(f"[EMU-GPU] Renderer: {renderer['nome']}")
        print(f"[EMU-GPU] CMD: {' '.join(cmd)}")

        def executar():
            try:
                proc = subprocess.Popen(cmd, env=env)
                proc.wait()
            except Exception as e:
                print(f"[EMU-GPU] Erro: {e}")

        threading.Thread(target=executar, daemon=True).start()

        messagebox.showinfo("Jogo Iniciado",
                           f"'{jogo.get('nome', 'jogo')}' foi iniciado!\n\n"
                           f"Renderer: {renderer['nome']}\n"
                           f"FPS: {fps_limit}\n"
                           f"Resolucao: {resolucao}")

    # =====================================================================
    # STATUS BAR
    # =====================================================================

    def _atualizar_status(self):
        try:
            with open('/proc/stat', 'r') as f:
                fields = list(map(int, f.readline().split()[1:]))
                cpu_pct = int(100 * (1 - fields[3] / sum(fields))) if sum(fields) > 0 else 0
            with open('/proc/meminfo', 'r') as f:
                lines = f.readlines()
                total_kb = int(lines[0].split()[1])
                avail_kb = int(lines[2].split()[1])
                used_pct = int(100 * (1 - avail_kb / total_kb))

            self.lbl_status_cpu.config(text=f"CPU: {cpu_pct}%",
                fg=COLORS["success"] if cpu_pct < 50 else COLORS["warning"] if cpu_pct < 80 else COLORS["danger"])
            self.lbl_status_ram.config(text=f"RAM: {used_pct}%")
        except:
            pass
        self.root.after(2000, self._atualizar_status)


def main():
    root = tk.Tk()
    try:
        icon_path = Path(__file__).parent.parent / "docs" / "icon.png"
        if icon_path.exists():
            img = tk.PhotoImage(file=str(icon_path))
            root.tk.call('wm', 'iconphoto', root._w, img)
    except:
        pass
    app = EmuGPUApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
