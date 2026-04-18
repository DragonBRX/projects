#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =============================================================================
# EMU-GPU TOOLKIT v1.0
# Uma ferramenta experimental para emular GPU via CPU e traduzir .exe
# Para CPUs potentes com GPUs fracas (como Intel HD 3000)
# =============================================================================

import argparse
import os
import sys
import json
import time
import signal
import shutil
import subprocess
import threading
from pathlib import Path
from typing import Optional, List, Dict, Any

# Verificar dependências opcionais
try:
    from colorama import Fore, Style, init
    init()
    HAS_COLOR = True
except ImportError:
    HAS_COLOR = False
    class _Fore:
        RED = '\033[31m'; GREEN = '\033[32m'; YELLOW = '\033[33m'
        BLUE = '\033[34m'; CYAN = '\033[36m'; MAGENTA = '\033[35m'
        WHITE = '\033[37m'; RESET = '\033[0m'
    class _Style:
        BRIGHT = '\033[1m'; RESET_ALL = '\033[0m'
    Fore = _Fore()
    Style = _Style()

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

# =============================================================================
# CONSTANTES E CONFIGURAÇÕES
# =============================================================================

VERSION = "1.0.0"
INSTALL_DIR = Path.home() / ".emu-gpu"
CONFIG_FILE = INSTALL_DIR / "config" / "settings.json"
GAMES_DIR = Path.home() / "Games" / "exe-translated"
LOG_FILE = INSTALL_DIR / "logs" / "emu-gpu.log"

# Configurações de renderização por software
SWRENDER_CONFIG = {
    "llvmpipe": {
        "name": "LLVMpipe (OpenGL por CPU)",
        "description": "Renderização OpenGL via LLVM/CPU. Compatível com jogos antigos e médios.",
        "env": {
            "LIBGL_ALWAYS_SOFTWARE": "1",
            "GALLIUM_DRIVER": "llvmpipe",
            "LP_NUM_THREADS": "0",  # 0 = auto (todos os threads)
            "MESA_GL_VERSION_OVERRIDE": "4.5",
            "MESA_GLSL_VERSION_OVERRIDE": "450",
            "MESA_NO_ERROR": "1",
            "__GL_THREADED_OPTIMIZATIONS": "1",
        },
        "performance_rating": "★★★☆☆",
        "compatibility_rating": "★★★★★",
    },
    "lavapipe": {
        "name": "Lavapipe (Vulkan por CPU)",
        "description": "Renderização Vulkan por software. Necessário para DXVK/VKD3D.",
        "env": {
            "VK_ICD_FILENAMES": "/usr/share/vulkan/icd.d/lvp_icd.x86_64.json",
            "DRI_PRIME": "0",
            "__GLX_VENDOR_LIBRARY_NAME": "mesa",
            "LIBGL_ALWAYS_SOFTWARE": "1",
        },
        "fallback_env": {
            "VK_ICD_FILENAMES": str(INSTALL_DIR / "config" / "lvp_icd.x86_64.json"),
        },
        "performance_rating": "★★☆☆☆",
        "compatibility_rating": "★★★★☆",
    },
    "swrender-full": {
        "name": "Software Render Full (Recomendado)",
        "description": "Combinação completa: OpenGL + Vulkan por software com Zink.",
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
        },
        "performance_rating": "★★★☆☆",
        "compatibility_rating": "★★★★★",
    },
    "virgl": {
        "name": "VirGL (Experimental)",
        "description": "Virtual GPU. Útil em VMs, menos recomendado para hardware real.",
        "env": {
            "LIBGL_ALWAYS_SOFTWARE": "1",
            "GALLIUM_DRIVER": "virpipe",
            "VIRGL_SERVER_PATH": "/tmp/virgl_hw",
        },
        "performance_rating": "★★☆☆☆",
        "compatibility_rating": "★★★☆☆",
    },
}

# =============================================================================
# CLASSE PRINCIPAL
# =============================================================================

class EmuGPUToolkit:
    def __init__(self):
        self.install_dir = INSTALL_DIR
        self.config_file = CONFIG_FILE
        self.config = self._load_config()
        self._setup_logging()
        
    def _load_config(self) -> Dict[str, Any]:
        """Carrega configurações do arquivo JSON"""
        default_config = {
            "version": VERSION,
            "default_renderer": "swrender-full",
            "fps_limit": 0,
            "cpu_affinity": True,
            "game_mode": False,
            "wine_prefix": str(Path.home() / ".wine"),
            "games_dir": str(GAMES_DIR),
            "dxvk_version": "1.10.3",
            "vkd3d_version": "2.11.1",
            "last_game": "",
            "installed_games": [],
        }
        
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    saved = json.load(f)
                    default_config.update(saved)
            except Exception as e:
                self._print(f"Aviso: Erro ao carregar config: {e}", color=Fore.YELLOW)
        
        return default_config
    
    def _save_config(self):
        """Salva configurações no arquivo JSON"""
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def _setup_logging(self):
        """Configura arquivo de log"""
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        
    def _log(self, message: str):
        """Escreve no arquivo de log"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(LOG_FILE, 'a') as f:
            f.write(f"[{timestamp}] {message}\n")
    
    def _print(self, message: str, color: str = Fore.WHITE, bold: bool = False):
        """Print colorido"""
        style = Style.BRIGHT if bold else ""
        print(f"{style}{color}{message}{Style.RESET_ALL}")
    
    def _print_banner(self):
        """Print banner principal"""
        self._print("╔══════════════════════════════════════════════════════════════╗", Fore.CYAN, True)
        self._print("║           EMU-GPU TOOLKIT v1.0                               ║", Fore.CYAN, True)
        self._print("║     GPU via CPU + Tradutor de .exe                           ║", Fore.CYAN, True)
        self._print("╚══════════════════════════════════════════════════════════════╝", Fore.CYAN, True)
        print()
    
    def _check_system(self) -> Dict[str, Any]:
        """Verifica e retorna informações do sistema"""
        info = {
            "cpu": "Desconhecido",
            "cores": 0,
            "threads": 0,
            "ram_gb": 0,
            "gpu": "Desconhecido",
            "mesa_version": "Desconhecido",
            "vulkan_available": False,
            "wine_available": False,
        }
        
        # CPU
        try:
            with open('/proc/cpuinfo', 'r') as f:
                content = f.read()
                for line in content.split('\n'):
                    if 'model name' in line and info["cpu"] == "Desconhecido":
                        info["cpu"] = line.split(':')[1].strip()
                info["threads"] = content.count('processor')
            info["cores"] = info["threads"] // 2 if info["threads"] > 1 else info["threads"]
        except:
            pass
        
        # RAM
        try:
            with open('/proc/meminfo', 'r') as f:
                mem_kb = int(f.readline().split()[1])
                info["ram_gb"] = mem_kb // 1048576
        except:
            pass
        
        # GPU
        try:
            result = subprocess.run(['lspci'], capture_output=True, text=True, timeout=5)
            for line in result.stdout.split('\n'):
                if 'vga' in line.lower() or '3d' in line.lower() or 'display' in line.lower():
                    info["gpu"] = line.split(':')[-1].strip()
                    break
        except:
            pass
        
        # Mesa
        try:
            result = subprocess.run(['glxinfo'], capture_output=True, text=True, timeout=5)
            for line in result.stdout.split('\n'):
                if 'OpenGL version' in line:
                    info["mesa_version"] = line.split(':')[-1].strip()
                    break
        except:
            pass
        
        # Vulkan
        try:
            result = subprocess.run(['vulkaninfo', '--summary'], capture_output=True, text=True, timeout=5)
            info["vulkan_available"] = 'deviceName' in result.stdout
        except:
            pass
        
        # Wine
        try:
            result = subprocess.run(['wine', '--version'], capture_output=True, text=True, timeout=5)
            info["wine_available"] = result.returncode == 0
            info["wine_version"] = result.stdout.strip() if result.returncode == 0 else "N/A"
        except:
            info["wine_available"] = False
            info["wine_version"] = "N/A"
        
        return info
    
    # =====================================================================
    # COMANDOS DA CLI
    # =====================================================================
    
    def cmd_status(self, args):
        """Mostra status do sistema e do toolkit"""
        self._print_banner()
        
        self._print("▶ STATUS DO SISTEMA", Fore.CYAN, True)
        print()
        
        info = self._check_system()
        
        self._print(f"  {'CPU:':<20} {info['cpu']}", Fore.WHITE)
        self._print(f"  {'Cores/Threads:':<20} {info['cores']} cores / {info['threads']} threads", Fore.WHITE)
        self._print(f"  {'RAM:':<20} {info['ram_gb']} GB", Fore.WHITE)
        self._print(f"  {'GPU Física:':<20} {info['gpu']}", Fore.WHITE)
        self._print(f"  {'Mesa/OpenGL:':<20} {info['mesa_version']}", Fore.WHITE)
        self._print(f"  {'Vulkan:':<20} {'Disponível ✓' if info['vulkan_available'] else 'Não disponível ✗'}", 
                     Fore.GREEN if info['vulkan_available'] else Fore.RED)
        self._print(f"  {'Wine:':<20} {info['wine_version']}", Fore.WHITE)
        print()
        
        self._print("▶ CONFIGURAÇÕES ATIVAS", Fore.CYAN, True)
        print()
        self._print(f"  {'Renderer padrão:':<20} {self.config['default_renderer']}", Fore.WHITE)
        self._print(f"  {'Limitador FPS:':<20} {self.config['fps_limit'] if self.config['fps_limit'] > 0 else 'Desativado'}", Fore.WHITE)
        self._print(f"  {'Afinidade CPU:':<20} {'Ativada ✓' if self.config['cpu_affinity'] else 'Desativada ✗'}", Fore.WHITE)
        self._print(f"  {'Game Mode:':<20} {'Ativado ✓' if self.config['game_mode'] else 'Desativado ✗'}", Fore.WHITE)
        self._print(f"  {'Wine prefix:':<20} {self.config['wine_prefix']}", Fore.WHITE)
        self._print(f"  {'Jogos instalados:':<20} {len(self.config['installed_games'])}", Fore.WHITE)
        print()
        
        # Verificar renderizadores disponíveis
        self._print("▶ RENDERIZADORES DISPONÍVEIS", Fore.CYAN, True)
        print()
        for key, renderer in SWRENDER_CONFIG.items():
            marker = " →" if key == self.config['default_renderer'] else "  "
            status = " [PADRÃO]" if key == self.config['default_renderer'] else ""
            self._print(f"{marker} {renderer['name']}{status}", Fore.GREEN if key == self.config['default_renderer'] else Fore.WHITE, 
                       key == self.config['default_renderer'])
            self._print(f"   Performance: {renderer['performance_rating']}  Compatibilidade: {renderer['compatibility_rating']}", Fore.YELLOW)
            self._print(f"   {renderer['description']}", Fore.WHITE)
            print()
    
    def cmd_run_cpu(self, args):
        """Roda um executável (.exe) com renderização por CPU"""
        self._print_banner()
        
        exe_path = args.exe_path
        if not os.path.exists(exe_path):
            self._print(f"Erro: Arquivo não encontrado: {exe_path}", Fore.RED)
            return 1
        
        # Verificar se é .exe ou outro executável
        is_exe = exe_path.lower().endswith('.exe')
        
        # Escolher renderer
        renderer_key = args.renderer or self.config['default_renderer']
        if renderer_key not in SWRENDER_CONFIG:
            self._print(f"Renderer desconhecido: {renderer_key}", Fore.RED)
            self._print(f"Renderizadores disponíveis: {', '.join(SWRENDER_CONFIG.keys())}", Fore.YELLOW)
            return 1
        
        renderer = SWRENDER_CONFIG[renderer_key]
        
        self._print("▶ INICIANDO EMULAÇÃO GPU VIA CPU", Fore.CYAN, True)
        print()
        self._print(f"  Programa:    {exe_path}", Fore.WHITE)
        self._print(f"  Renderer:    {renderer['name']}", Fore.WHITE)
        self._print(f"  Modo:        {'OpenGL' if 'llvmpipe' in renderer_key else 'Vulkan' if 'lavapipe' in renderer_key else 'Híbrido'}", Fore.WHITE)
        print()
        
        # Construir ambiente
        env = os.environ.copy()
        env.update(renderer['env'])
        
        # Verificar se VK_ICD_FILENAMES existe
        if 'VK_ICD_FILENAMES' in env:
            icd_path = env['VK_ICD_FILENAMES']
            if not os.path.exists(icd_path):
                # Tentar encontrar o arquivo
                try:
                    result = subprocess.run(['find', '/usr', '-name', 'lvp_icd*.json'], 
                                          capture_output=True, text=True, timeout=10)
                    if result.stdout.strip():
                        env['VK_ICD_FILENAMES'] = result.stdout.strip().split('\n')[0]
                        self._print(f"  ICD encontrado: {env['VK_ICD_FILENAMES']}", Fore.YELLOW)
                except:
                    pass
        
        # Configurar Wine se for .exe
        if is_exe:
            env['WINEPREFIX'] = self.config['wine_prefix']
            # Verificar se DXVK está instalado
            dxvk_dir = self.install_dir / "dxvk"
            if dxvk_dir.exists():
                self._print("  DXVK:        Disponível para tradução DirectX → Vulkan", Fore.GREEN)
        
        # Configurar afinidade de CPU
        cmd = []
        if self.config['cpu_affinity'] or args.cpu_affinity:
            total = os.cpu_count() or 4
            physical = total // 2
            affinity = f"0-{physical-1}" if physical > 1 else "0"
            cmd = ['taskset', '-c', affinity]
            self._print(f"  CPU Affinity: Cores {affinity}", Fore.WHITE)
        
        # Limitador de FPS
        if self.config['fps_limit'] > 0 or args.fps_limit > 0:
            fps = args.fps_limit or self.config['fps_limit']
            env['__GL_SYNC_TO_VBLANK'] = '1'
            env['vblank_mode'] = '1'
            self._print(f"  FPS Limit:   {fps}", Fore.WHITE)
        
        # Comando final
        if is_exe:
            cmd.extend(['wine', exe_path] + (args.args or []))
        else:
            cmd.append(exe_path)
            if args.args:
                cmd.extend(args.args)
        
        print()
        self._print("▶ Pressione Ctrl+C para encerrar", Fore.YELLOW)
        self._print("═══════════════════════════════════════════════════════════════", Fore.CYAN)
        print()
        
        # Executar
        self._log(f"Iniciando: {' '.join(cmd)} com renderer {renderer_key}")
        
        try:
            process = subprocess.Popen(cmd, env=env)
            
            # Monitor de performance em thread separada
            if HAS_PSUTIL and args.monitor:
                monitor_thread = threading.Thread(target=self._monitor_performance, args=(process.pid,))
                monitor_thread.daemon = True
                monitor_thread.start()
            
            process.wait()
            return process.returncode
            
        except KeyboardInterrupt:
            self._print("\nPrograma interrompido pelo usuário.", Fore.YELLOW)
            if 'process' in locals():
                process.terminate()
                try:
                    process.wait(timeout=5)
                except:
                    process.kill()
            return 130
        except Exception as e:
            self._print(f"Erro ao executar: {e}", Fore.RED)
            return 1
    
    def _monitor_performance(self, pid: int):
        """Monitora uso de CPU e memória do processo"""
        try:
            process = psutil.Process(pid)
            while process.is_running():
                cpu = process.cpu_percent(interval=1)
                mem = process.memory_info().rss / 1024 / 1024  # MB
                self._print(f"  [MONITOR] CPU: {cpu:5.1f}% | RAM: {mem:6.0f} MB", Fore.MAGENTA)
        except:
            pass
    
    def cmd_benchmark(self, args):
        """Roda benchmark de renderização por software"""
        self._print_banner()
        self._print("▶ BENCHMARK DE RENDERIZAÇÃO POR SOFTWARE", Fore.CYAN, True)
        print()
        
        renderer_key = args.renderer or self.config['default_renderer']
        renderer = SWRENDER_CONFIG.get(renderer_key, SWRENDER_CONFIG['swrender-full'])
        
        self._print(f"Renderer: {renderer['name']}", Fore.WHITE)
        print()
        
        # Verificar glxinfo
        self._print("▶ Teste 1/3: Informações OpenGL...", Fore.YELLOW)
        env = os.environ.copy()
        env.update(renderer['env'])
        
        try:
            result = subprocess.run(['glxinfo'], capture_output=True, text=True, env=env, timeout=10)
            if 'llvmpipe' in result.stdout or 'Lavapipe' in result.stdout:
                self._print("  ✓ Renderização por software detectada", Fore.GREEN)
            else:
                self._print("  ⚠ Renderização por software NÃO detectada", Fore.YELLOW)
            
            # Extrair versão OpenGL
            for line in result.stdout.split('\n'):
                if 'OpenGL version' in line or 'OpenGL core profile version' in line:
                    self._print(f"  {line}", Fore.WHITE)
                    break
        except Exception as e:
            self._print(f"  ✗ Falha: {e}", Fore.RED)
        
        # Teste Vulkan
        self._print("\n▶ Teste 2/3: Informações Vulkan...", Fore.YELLOW)
        try:
            result = subprocess.run(['vulkaninfo', '--summary'], capture_output=True, text=True, env=env, timeout=10)
            if 'LAVAPIPE' in result.stdout.upper() or 'llvmpipe' in result.stdout.lower():
                self._print("  ✓ Vulkan por software (Lavapipe) detectado", Fore.GREEN)
            else:
                self._print("  ⚠ Lavapipe não detectado", Fore.YELLOW)
        except Exception as e:
            self._print(f"  ✗ Falha: {e}", Fore.RED)
        
        # Teste glxgears
        self._print("\n▶ Teste 3/3: Performance GLXGears (5 segundos)...", Fore.YELLOW)
        try:
            result = subprocess.run(['timeout', '5', 'glxgears'], 
                                  capture_output=True, text=True, env=env, timeout=10)
            output = result.stderr if result.stderr else result.stdout
            for line in output.split('\n'):
                if 'FPS' in line or 'frames' in line.lower():
                    self._print(f"  {line.strip()}", Fore.GREEN)
                    break
        except Exception as e:
            self._print(f"  ⚠ Teste interrompido: {e}", Fore.YELLOW)
        
        print()
        self._print("Benchmark concluído!", Fore.GREEN, True)
    
    def cmd_install_exe(self, args):
        """Instala um arquivo .exe (setup/installer)"""
        self._print_banner()
        
        setup_path = args.setup_path
        if not os.path.exists(setup_path):
            self._print(f"Erro: Arquivo não encontrado: {setup_path}", Fore.RED)
            return 1
        
        # Criar diretório do jogo
        game_name = args.name or Path(setup_path).stem
        game_dir = GAMES_DIR / game_name
        game_dir.mkdir(parents=True, exist_ok=True)
        
        self._print("▶ INSTALANDO APLICAÇÃO .EXE", Fore.CYAN, True)
        print()
        self._print(f"  Setup: {setup_path}", Fore.WHITE)
        self._print(f"  Nome:  {game_name}", Fore.WHITE)
        self._print(f"  Destino: {game_dir}", Fore.WHITE)
        print()
        
        # Configurar Wine para instalação
        env = os.environ.copy()
        env['WINEPREFIX'] = str(game_dir / "wine_prefix")
        env['WINEARCH'] = 'win64'
        
        # Inicializar prefixo
        self._print("▶ Inicializando prefixo Wine...", Fore.YELLOW)
        try:
            subprocess.run(['winecfg', '/v=win10'], env=env, check=True, timeout=60)
        except Exception as e:
            self._print(f"Aviso: {e}", Fore.YELLOW)
        
        # Rodar instalador
        self._print("▶ Rodando instalador (siga as instruções na tela)...", Fore.YELLOW)
        try:
            subprocess.run(['wine', setup_path], env=env, check=True)
        except subprocess.CalledProcessError:
            self._print("Instalação retornou erro (pode ser normal).", Fore.YELLOW)
        
        # Salvar na configuração
        game_info = {
            "name": game_name,
            "dir": str(game_dir),
            "prefix": str(game_dir / "wine_prefix"),
            "installed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        
        self.config['installed_games'].append(game_info)
        self._save_config()
        
        self._print(f"\n✓ {game_name} instalado!", Fore.GREEN, True)
        self._print(f"  Para rodar: emu-gpu play \"{game_name}\"", Fore.CYAN)
    
    def cmd_play(self, args):
        """Roda um jogo instalado"""
        game_name = args.game_name
        
        # Procurar jogo
        game_info = None
        for game in self.config['installed_games']:
            if game['name'].lower() == game_name.lower():
                game_info = game
                break
        
        if not game_info:
            self._print(f"Jogo não encontrado: {game_name}", Fore.RED)
            self._print("Jogos instalados:", Fore.YELLOW)
            for game in self.config['installed_games']:
                self._print(f"  - {game['name']}", Fore.WHITE)
            return 1
        
        # Procurar executável no diretório do jogo
        game_dir = Path(game_info['dir'])
        exe_files = list(game_dir.rglob("*.exe"))
        
        if not exe_files:
            self._print("Nenhum .exe encontrado no diretório do jogo.", Fore.RED)
            return 1
        
        # Se houver múltiplos, tentar encontrar o principal
        main_exe = exe_files[0]
        for exe in exe_files:
            name_lower = exe.name.lower()
            if 'launcher' in name_lower or 'start' in name_lower or game_name.lower() in name_lower:
                main_exe = exe
                break
        
        # Perguntar qual executável se houver múltiplos e não for automático
        if len(exe_files) > 1 and not args.exe:
            self._print("Múltiplos executáveis encontrados:", Fore.YELLOW)
            for i, exe in enumerate(exe_files[:10]):
                marker = " ← sugerido" if exe == main_exe else ""
                self._print(f"  {i+1}. {exe.name}{marker}", Fore.WHITE)
            
            if len(exe_files) > 10:
                self._print(f"  ... e mais {len(exe_files)-10}", Fore.WHITE)
            
            choice = input("\nQual executável rodar? (número ou caminho): ").strip()
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(exe_files):
                    main_exe = exe_files[idx]
            except ValueError:
                if os.path.exists(choice):
                    main_exe = Path(choice)
        elif args.exe:
            main_exe = Path(args.exe)
        
        self._print(f"\nExecutando: {main_exe}", Fore.CYAN)
        
        # Configurar e rodar
        args.exe_path = str(main_exe)
        args.renderer = args.renderer or self.config['default_renderer']
        args.args = []
        args.cpu_affinity = True
        args.fps_limit = 0
        args.monitor = args.monitor if hasattr(args, 'monitor') else False
        
        # Usar o prefixo Wine correto
        old_prefix = self.config['wine_prefix']
        self.config['wine_prefix'] = game_info['prefix']
        
        result = self.cmd_run_cpu(args)
        
        self.config['wine_prefix'] = old_prefix
        return result
    
    def cmd_list_games(self, args):
        """Lista jogos instalados"""
        self._print_banner()
        self._print("▶ JOGOS INSTALADOS", Fore.CYAN, True)
        print()
        
        if not self.config['installed_games']:
            self._print("Nenhum jogo instalado.", Fore.YELLOW)
            self._print("Para instalar: emu-gpu install /caminho/para/setup.exe", Fore.WHITE)
            return
        
        for i, game in enumerate(self.config['installed_games'], 1):
            self._print(f"{i}. {game['name']}", Fore.GREEN, True)
            self._print(f"   Diretório: {game['dir']}", Fore.WHITE)
            self._print(f"   Instalado: {game['installed_at']}", Fore.WHITE)
            print()
    
    def cmd_translate_exe(self, args):
        """Analisa e prepara um .exe para execução"""
        self._print_banner()
        
        exe_path = args.exe_path
        if not os.path.exists(exe_path):
            self._print(f"Erro: Arquivo não encontrado: {exe_path}", Fore.RED)
            return 1
        
        self._print("▶ ANÁLISE E TRADUÇÃO DE .EXE", Fore.CYAN, True)
        print()
        self._print(f"Arquivo: {exe_path}", Fore.WHITE)
        
        # Detectar tipo de executável
        self._print("\n▶ Detectando tipo de executável...", Fore.YELLOW)
        
        try:
            # Verificar se é PE32/PE32+
            result = subprocess.run(['file', exe_path], capture_output=True, text=True, timeout=10)
            file_info = result.stdout.strip()
            self._print(f"  {file_info}", Fore.WHITE)
            
            if 'PE32+' in file_info:
                self._print("  Tipo: Executável Windows 64-bit", Fore.GREEN)
            elif 'PE32' in file_info:
                self._print("  Tipo: Executável Windows 32-bit", Fore.GREEN)
            elif 'Mono' in file_info or '.NET' in file_info:
                self._print("  Tipo: Executável .NET/Mono", Fore.GREEN)
            
        except Exception as e:
            self._print(f"  Erro na detecção: {e}", Fore.RED)
        
        # Verificar dependências com wine
        self._print("\n▶ Verificando dependências...", Fore.YELLOW)
        try:
            env = os.environ.copy()
            env['WINEPREFIX'] = self.config['wine_prefix']
            result = subprocess.run(['wine', 'dumpbin', '/dependents', exe_path], 
                                  capture_output=True, text=True, env=env, timeout=15)
            if result.returncode == 0:
                self._print("  Dependências encontradas:", Fore.GREEN)
                for line in result.stdout.split('\n')[:20]:
                    if '.dll' in line.lower():
                        self._print(f"    {line.strip()}", Fore.WHITE)
            else:
                # Tentar com ldd
                result = subprocess.run(['ldd', exe_path], capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    self._print("  Bibliotecas:", Fore.GREEN)
                    for line in result.stdout.split('\n')[:15]:
                        if line.strip():
                            self._print(f"    {line.strip()}", Fore.WHITE)
        except Exception as e:
            self._print(f"  Não foi possível verificar dependências: {e}", Fore.YELLOW)
        
        # Recomendações
        self._print("\n▶ RECOMENDAÇÕES", Fore.CYAN, True)
        print()
        
        self._print("Para rodar este executável:", Fore.WHITE)
        self._print(f"  emu-gpu run-cpu \"{exe_path}\"", Fore.CYAN, True)
        print()
        
        # Verificar se o executável parece ser um jogo
        game_indicators = ['game', 'jogo', 'engine', 'directx', 'd3d', 'opengl', 'vulkan', 
                          'unity', 'unreal', 'cry', 'frostbite', 'source']
        
        is_game = any(ind in file_info.lower() for ind in game_indicators)
        
        if is_game or args.exe_path.lower().endswith('.exe'):
            self._print("Este parece ser um jogo/executável gráfico.", Fore.YELLOW)
            self._print("Recomendações de renderer:", Fore.WHITE)
            
            # Analisar tamanho para estimar complexidade
            size_mb = os.path.getsize(exe_path) / (1024 * 1024)
            
            if size_mb < 50:
                self._print(f"  → llvmpipe (jogo leve, ~{size_mb:.0f}MB)", Fore.GREEN)
            elif size_mb < 500:
                self._print(f"  → swrender-full (jogo médio, ~{size_mb:.0f}MB)", Fore.GREEN)
            else:
                self._print(f"  → swrender-full com limitador de FPS (jogo pesado, ~{size_mb:.0f}MB)", Fore.GREEN)
                self._print("    Sugestão: emu-gpu run-cpu --fps-limit 30 ", Fore.CYAN)
    
    def cmd_config(self, args):
        """Gerencia configurações"""
        if args.key:
            if args.value:
                # Set
                self.config[args.key] = self._cast_value(args.value)
                self._save_config()
                self._print(f"✓ {args.key} = {self.config[args.key]}", Fore.GREEN)
            else:
                # Get
                value = self.config.get(args.key, "Não definido")
                self._print(f"{args.key} = {value}", Fore.CYAN)
        else:
            # List all
            self._print_banner()
            self._print("▶ CONFIGURAÇÕES", Fore.CYAN, True)
            print()
            for key, value in sorted(self.config.items()):
                self._print(f"  {key:<25} = {value}", Fore.WHITE)
    
    def _cast_value(self, value: str) -> Any:
        """Converte string para tipo apropriado"""
        if value.lower() in ('true', 'yes', 'on'):
            return True
        if value.lower() in ('false', 'no', 'off'):
            return False
        try:
            return int(value)
        except ValueError:
            try:
                return float(value)
            except ValueError:
                return value
    
    def cmd_monitor(self, args):
        """Monitora uso de CPU/GPU em tempo real"""
        if not HAS_PSUTIL:
            self._print("psutil não instalado. Rode: pip install psutil", Fore.RED)
            return 1
        
        self._print_banner()
        self._print("▶ MONITOR DE SISTEMA (Ctrl+C para sair)", Fore.CYAN, True)
        print()
        
        try:
            while True:
                # CPU
                cpu_percent = psutil.cpu_percent(interval=1, percpu=True)
                cpu_avg = sum(cpu_percent) / len(cpu_percent)
                
                # Memória
                mem = psutil.virtual_memory()
                
                # Temperatura (se disponível)
                temps = "N/A"
                try:
                    if hasattr(psutil, 'sensors_temperatures'):
                        temps_data = psutil.sensors_temperatures()
                        if temps_data:
                            for name, entries in temps_data.items():
                                if entries:
                                    temps = f"{entries[0].current:.0f}°C"
                                    break
                except:
                    pass
                
                # Barra visual de CPU
                bar_len = 20
                filled = int(cpu_avg / 100 * bar_len)
                bar = '█' * filled + '░' * (bar_len - filled)
                
                # Cor baseado no uso
                color = Fore.GREEN if cpu_avg < 50 else Fore.YELLOW if cpu_avg < 80 else Fore.RED
                
                status = f"\r  CPU: [{bar}] {cpu_avg:5.1f}% | RAM: {mem.percent:5.1f}% | Temp: {temps}"
                self._print(status, color, end='\r')
                
        except KeyboardInterrupt:
            print()
            self._print("\nMonitor encerrado.", Fore.YELLOW)


# =============================================================================
# MAIN / ARGPARSE
# =============================================================================

def main():
    toolkit = EmuGPUToolkit()
    
    parser = argparse.ArgumentParser(
        prog='emu-gpu',
        description='EMU-GPU Toolkit - GPU via CPU e tradutor de .exe',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  emu-gpu status                          Ver status do sistema
  emu-gpu run-cpu jogo.exe                Rodar jogo com GPU via CPU
  emu-gpu run-cpu --fps-limit 30 jogo.exe Rodar com limite de 30 FPS
  emu-gpu benchmark                       Testar performance de renderização
  emu-gpu install ./setup.exe             Instalar aplicativo .exe
  emu-gpu play "Nome do Jogo"             Rodar jogo instalado
  emu-gpu translate jogo.exe              Analisar executável
  emu-gpu config default_renderer llvmpipe Mudar renderer padrão
  emu-gpu monitor                         Monitorar CPU em tempo real
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Comandos disponíveis')
    
    # status
    status_parser = subparsers.add_parser('status', help='Status do sistema')
    
    # run-cpu
    run_parser = subparsers.add_parser('run-cpu', help='Roda .exe com renderização por CPU')
    run_parser.add_argument('exe_path', help='Caminho para o executável')
    run_parser.add_argument('args', nargs='*', help='Argumentos para o executável')
    run_parser.add_argument('--renderer', '-r', choices=list(SWRENDER_CONFIG.keys()),
                           help='Renderer a usar')
    run_parser.add_argument('--fps-limit', '-f', type=int, default=0,
                           help='Limite de FPS (0 = sem limite)')
    run_parser.add_argument('--cpu-affinity', '-a', action='store_true',
                           help='Usar afinidade de CPU otimizada')
    run_parser.add_argument('--monitor', '-m', action='store_true',
                           help='Monitorar performance em tempo real')
    
    # benchmark
    bench_parser = subparsers.add_parser('benchmark', help='Benchmark de renderização')
    bench_parser.add_argument('--renderer', '-r', choices=list(SWRENDER_CONFIG.keys()),
                             help='Renderer a testar')
    
    # install
    install_parser = subparsers.add_parser('install', help='Instala .exe')
    install_parser.add_argument('setup_path', help='Caminho para o instalador')
    install_parser.add_argument('--name', '-n', help='Nome do jogo')
    
    # play
    play_parser = subparsers.add_parser('play', help='Roda jogo instalado')
    play_parser.add_argument('game_name', help='Nome do jogo')
    play_parser.add_argument('--exe', '-e', help='Executável específico')
    play_parser.add_argument('--renderer', '-r', choices=list(SWRENDER_CONFIG.keys()))
    play_parser.add_argument('--monitor', '-m', action='store_true')
    
    # list-games
    list_parser = subparsers.add_parser('list-games', help='Lista jogos instalados')
    
    # translate
    trans_parser = subparsers.add_parser('translate', help='Analisa e prepara .exe')
    trans_parser.add_argument('exe_path', help='Caminho para o executável')
    
    # config
    config_parser = subparsers.add_parser('config', help='Gerencia configurações')
    config_parser.add_argument('key', nargs='?', help='Chave de configuração')
    config_parser.add_argument('value', nargs='?', help='Valor a definir')
    
    # monitor
    monitor_parser = subparsers.add_parser('monitor', help='Monitor de sistema')
    
    # Parse args
    args = parser.parse_args()
    
    if not args.command:
        toolkit._print_banner()
        parser.print_help()
        return 0
    
    # Dispatch
    commands = {
        'status': toolkit.cmd_status,
        'run-cpu': toolkit.cmd_run_cpu,
        'benchmark': toolkit.cmd_benchmark,
        'install': toolkit.cmd_install_exe,
        'play': toolkit.cmd_play,
        'list-games': toolkit.cmd_list_games,
        'translate': toolkit.cmd_translate_exe,
        'config': toolkit.cmd_config,
        'monitor': toolkit.cmd_monitor,
    }
    
    if args.command in commands:
        try:
            return commands[args.command](args) or 0
        except Exception as e:
            toolkit._print(f"Erro: {e}", Fore.RED)
            toolkit._log(f"Erro no comando {args.command}: {e}")
            return 1
    else:
        parser.print_help()
        return 1

if __name__ == '__main__':
    sys.exit(main())
