#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EMU-GPU Toolkit v2.0 - Sistema de Configuracao
"""

import os
import json
from pathlib import Path
from datetime import datetime

# Diretorios
HOME = Path.home()
INSTALL_DIR = HOME / ".emu-gpu"
CONFIG_DIR = INSTALL_DIR / "config"
GAMES_DIR = HOME / "Games" / "emu-gpu-library"
TRANSLATOR_DIR = INSTALL_DIR / "translator"
RENDERERS_DIR = INSTALL_DIR / "renderers"
CACHE_DIR = INSTALL_DIR / "cache"
LOGS_DIR = INSTALL_DIR / "logs"

# Arquivos
SETTINGS_FILE = CONFIG_DIR / "settings.json"
GAMES_DB = CONFIG_DIR / "games.json"

# Cores tema escuro
COLORS = {
    "bg_dark": "#0d1117",
    "bg_darker": "#010409",
    "bg_card": "#161b22",
    "bg_hover": "#1f2937",
    "bg_active": "#21262d",
    "border": "#30363d",
    "border_hover": "#8b949e",
    "text": "#e6edf3",
    "text_secondary": "#8b949e",
    "text_muted": "#6e7681",
    "accent": "#58a6ff",
    "accent_hover": "#79b8ff",
    "success": "#3fb950",
    "success_hover": "#46cc55",
    "warning": "#d29922",
    "danger": "#f85149",
    "purple": "#bc8cff",
    "cyan": "#39d0d8",
    "pink": "#f778ba",
}

# Renderizadores disponiveis
RENDERERS = {
    "llvmpipe": {
        "id": "llvmpipe",
        "nome": "OpenGL por CPU",
        "subtitulo": "LLVMpipe",
        "desc": "Melhor para jogos 2D e leves. Maxima compatibilidade com hardware antigo.",
        "icone": "󰌽",
        "cor": "#3fb950",
        "cor_bg": "rgba(63, 185, 80, 0.15)",
        "fps_sug": 60,
        "categoria": "2D / Leve",
        "env": {
            "LIBGL_ALWAYS_SOFTWARE": "1",
            "GALLIUM_DRIVER": "llvmpipe",
            "LP_NUM_THREADS": "0",
            "MESA_GL_VERSION_OVERRIDE": "4.5",
            "MESA_GLSL_VERSION_OVERRIDE": "450",
            "MESA_NO_ERROR": "1",
            "__GL_THREADED_OPTIMIZATIONS": "1",
        }
    },
    "lavapipe": {
        "id": "lavapipe",
        "nome": "Vulkan por CPU",
        "subtitulo": "Lavapipe",
        "desc": "Para jogos com DXVK. DirectX 9/10/11 via Vulkan por software.",
        "icone": "󰌋",
        "cor": "#bc8cff",
        "cor_bg": "rgba(188, 140, 255, 0.15)",
        "fps_sug": 30,
        "categoria": "3D / DXVK",
        "env": {
            "VK_ICD_FILENAMES": "/usr/share/vulkan/icd.d/lvp_icd.x86_64.json",
            "LIBGL_ALWAYS_SOFTWARE": "1",
            "DRI_PRIME": "0",
            "__GLX_VENDOR_LIBRARY_NAME": "mesa",
        }
    },
    "swrender-full": {
        "id": "swrender-full",
        "nome": "Render Completo",
        "subtitulo": "OpenGL + Vulkan + Zink",
        "desc": "Combina LLVMpipe + Lavapipe + Zink. Melhor resultado geral para jogos modernos.",
        "icone": "󰨜",
        "cor": "#58a6ff",
        "cor_bg": "rgba(88, 166, 255, 0.15)",
        "fps_sug": 30,
        "categoria": "Completo",
        "env": {
            "LIBGL_ALWAYS_SOFTWARE": "1",
            "GALLIUM_DRIVER": "llvmpipe",
            "LP_NUM_THREADS": "0",
            "MESA_GL_VERSION_OVERRIDE": "4.5",
            "MESA_GLSL_VERSION_OVERRIDE": "450",
            "MESA_LOADER_DRIVER_OVERRIDE": "zink",
            "VK_ICD_FILENAMES": "/usr/share/vulkan/icd.d/lvp_icd.x86_64.json",
            "DRI_PRIME": "0",
            "__GLX_VENDOR_LIBRARY_NAME": "mesa",
            "MESA_NO_ERROR": "1",
            "__GL_THREADED_OPTIMIZATIONS": "1",
        }
    },
}

# Modulos de traducao disponiveis
TRANSLATION_MODULES = {
    "dxvk": {
        "id": "dxvk",
        "nome": "DXVK",
        "desc": "DirectX 9/10/11 → Vulkan (codigo aberto)",
        "repo": "https://github.com/doitsujin/dxvk",
        "versao": "2.3.1",
        "compat": ["d3d9", "d3d10", "d3d11", "dxgi"],
    },
    "vkd3d": {
        "id": "vkd3d",
        "nome": "VKD3D-Proton",
        "desc": "DirectX 12 → Vulkan (codigo aberto)",
        "repo": "https://github.com/HansKristian-Work/vkd3d-proton",
        "versao": "2.11.1",
        "compat": ["d3d12"],
    },
    "wined3d": {
        "id": "wined3d",
        "nome": "WineD3D",
        "desc": "DirectX → OpenGL (integrado Wine)",
        "repo": "https://gitlab.winehq.org/wine/wine",
        "versao": "9.0",
        "compat": ["d3d8", "d3d9", "d3d10", "d3d11"],
    },
    "faudio": {
        "id": "faudio",
        "nome": "FAudio",
        "desc": "XAudio2 reimplementacao (codigo aberto)",
        "repo": "https://github.com/FNA-XNA/FAudio",
        "versao": "24.06",
        "compat": ["xaudio2", "x3daudio"],
    },
    "battleye": {
        "id": "battleye",
        "nome": "BattlEye Bridge",
        "desc": "Suporte a anti-cheat BattlEye (Proton)",
        "repo": "https://github.com/ValveSoftware/Proton",
        "versao": "experimental",
        "compat": ["anticheat"],
    },
    "eac": {
        "id": "eac",
        "nome": "EAC Bridge",
        "desc": "Suporte a Easy Anti-Cheat (Proton)",
        "repo": "https://github.com/ValveSoftware/Proton",
        "versao": "experimental",
        "compat": ["anticheat"],
    },
}


def init_directories():
    """Cria estrutura de diretorios necessaria"""
    for d in [CONFIG_DIR, GAMES_DIR, TRANSLATOR_DIR, RENDERERS_DIR, 
              CACHE_DIR, LOGS_DIR, INSTALL_DIR / "wrappers"]:
        d.mkdir(parents=True, exist_ok=True)


def load_settings():
    """Carrega configuracoes do usuario"""
    default = {
        "version": "2.0",
        "default_renderer": "swrender-full",
        "fps_limit": 30,
        "resolucao": "1280x720",
        "cpu_affinity": True,
        "game_mode": False,
        "janela": True,
        "ultimo_diretorio": str(HOME / "Downloads"),
        "translators_ativos": ["dxvk", "faudio"],
        "experimental_tools": {
            "fsr": False,
            "frame_gen": False,
            "shader_cache": True,
        },
        "theme": "dark",
        "notifications": True,
    }
    
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, 'r') as f:
                saved = json.load(f)
                default.update(saved)
        except:
            pass
    
    return default


def save_settings(cfg):
    """Salva configuracoes do usuario"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


def load_games():
    """Carrega biblioteca de jogos"""
    if GAMES_DB.exists():
        try:
            with open(GAMES_DB, 'r') as f:
                return json.load(f)
        except:
            return []
    return []


def save_games(games):
    """Salva biblioteca de jogos"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(GAMES_DB, 'w') as f:
        json.dump(games, f, indent=2, ensure_ascii=False)


def add_game(game_data):
    """Adiciona um jogo a biblioteca"""
    games = load_games()
    # Remove duplicado pelo nome
    games = [g for g in games if g.get("nome") != game_data["nome"]]
    game_data["adicionado"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    game_data["id"] = f"game_{int(datetime.now().timestamp())}"
    games.append(game_data)
    save_games(games)
    return game_data


def remove_game(game_id):
    """Remove um jogo da biblioteca"""
    games = load_games()
    games = [g for g in games if g.get("id") != game_id]
    save_games(games)
