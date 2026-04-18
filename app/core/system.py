#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EMU-GPU Toolkit v2.0 - Deteccao de Sistema e Hardware
"""

import os
import re
import subprocess
from pathlib import Path


def get_cpu_info():
    """Obtem informacoes detalhadas da CPU"""
    info = {
        "modelo": "Desconhecido",
        "cores_fisicos": 0,
        "threads": 0,
        "freq_max": "Desconhecida",
        "arquitetura": "Desconhecida",
        "flags": [],
    }
    
    try:
        with open('/proc/cpuinfo', 'r') as f:
            content = f.read()
            
        for line in content.split('\n'):
            if 'model name' in line and info["modelo"] == "Desconhecido":
                info["modelo"] = line.split(':')[1].strip()
            if 'cpu cores' in line and info["cores_fisicos"] == 0:
                info["cores_fisicos"] = int(line.split(':')[1].strip())
                
        info["threads"] = content.count('processor')
        
        if info["cores_fisicos"] == 0:
            info["cores_fisicos"] = info["threads"] // 2 if info["threads"] > 1 else info["threads"]
            
        # Frequencia maxima
        try:
            with open('/sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq', 'r') as f:
                freq_khz = int(f.read().strip())
                info["freq_max"] = f"{freq_khz / 1000000:.2f} GHz"
        except:
            pass
            
        # Arquitetura
        try:
            result = subprocess.run(['uname', '-m'], capture_output=True, text=True, timeout=2)
            info["arquitetura"] = result.stdout.strip()
        except:
            pass
            
        # Flags (AVX, SSE, etc)
        flags_match = re.search(r'flags\s*:.*', content)
        if flags_match:
            flags = flags_match.group().split(':')[1].strip().split()
            info["flags"] = [f for f in flags if any(x in f for x in ['sse', 'avx', 'mmx', 'fma'])]
            
    except Exception as e:
        print(f"[SYSTEM] Erro ao detectar CPU: {e}")
        
    return info


def get_ram_info():
    """Obtem informacoes de RAM"""
    info = {"total_gb": 0, "disponivel_gb": 0, "uso_percent": 0}
    
    try:
        with open('/proc/meminfo', 'r') as f:
            lines = f.readlines()
            
        total_kb = int(lines[0].split()[1])  # MemTotal
        available_kb = int(lines[2].split()[1])  # MemAvailable
        
        info["total_gb"] = round(total_kb / 1048576, 1)
        info["disponivel_gb"] = round(available_kb / 1048576, 1)
        info["uso_percent"] = int(100 * (1 - available_kb / total_kb))
        
    except Exception as e:
        print(f"[SYSTEM] Erro ao detectar RAM: {e}")
        
    return info


def get_gpu_info():
    """Obtem informacoes da GPU"""
    info = {"modelo": "Nao detectada", "driver": "Desconhecido", "vulkan": False, "opengl": "Desconhecido"}
    
    try:
        result = subprocess.run(['lspci'], capture_output=True, text=True, timeout=5)
        for line in result.stdout.split('\n'):
            if 'vga' in line.lower() or '3d' in line.lower() or 'display' in line.lower():
                info["modelo"] = line.split(':')[-1].strip()
                break
    except:
        pass
    
    # Verificar Vulkan
    try:
        result = subprocess.run(['vulkaninfo', '--summary'], capture_output=True, text=True, timeout=5)
        info["vulkan"] = 'deviceName' in result.stdout
        if info["vulkan"]:
            match = re.search(r'deviceName\s*=\s*(.+)', result.stdout)
            if match:
                info["vulkan_device"] = match.group(1).strip()
    except:
        pass
    
    # Verificar OpenGL
    try:
        result = subprocess.run(['glxinfo'], capture_output=True, text=True, timeout=5)
        match = re.search(r'OpenGL renderer string: (.+)', result.stdout)
        if match:
            info["opengl"] = match.group(1).strip()
    except:
        pass
    
    return info


def check_componentes():
    """Verifica status dos componentes necessarios"""
    status = {
        "vulkan": False,
        "mesa": False,
        "llvmpipe": False,
        "lavapipe": False,
        "python3": False,
        "zenity": False,
        "nautilus": False,
        "translators": {},
    }
    
    # Vulkan
    try:
        result = subprocess.run(['vulkaninfo', '--summary'], capture_output=True, text=True, timeout=5)
        status["vulkan"] = result.returncode == 0
    except:
        pass
    
    # Mesa
    try:
        result = subprocess.run(['glxinfo'], capture_output=True, text=True, timeout=5)
        status["mesa"] = 'Mesa' in result.stdout
        status["llvmpipe"] = 'llvmpipe' in result.stdout
    except:
        pass
    
    # Lavapipe ICD
    icd_path = "/usr/share/vulkan/icd.d/lvp_icd.x86_64.json"
    status["lavapipe"] = os.path.exists(icd_path)
    
    # Python3
    try:
        result = subprocess.run(['python3', '--version'], capture_output=True, text=True, timeout=2)
        status["python3"] = result.returncode == 0
    except:
        pass
    
    # Zenity (file picker nativo)
    try:
        result = subprocess.run(['zenity', '--version'], capture_output=True, text=True, timeout=2)
        status["zenity"] = result.returncode == 0
    except:
        pass
    
    # Nautilus (file manager nativo)
    try:
        result = subprocess.run(['nautilus', '--version'], capture_output=True, text=True, timeout=2)
        status["nautilus"] = result.returncode == 0
    except:
        pass
    
    # Translators instalados
    from .config import TRANSLATOR_DIR
    for mod in ["dxvk", "vkd3d", "wined3d", "faudio"]:
        mod_dir = TRANSLATOR_DIR / mod
        status["translators"][mod] = mod_dir.exists()
    
    return status


def get_cpu_usage():
    """Retorna uso percentual da CPU"""
    try:
        with open('/proc/stat', 'r') as f:
            fields = list(map(int, f.readline().split()[1:]))
            total = sum(fields)
            idle = fields[3]
            return int(100 * (1 - idle / total)) if total > 0 else 0
    except:
        return 0


def get_ram_usage():
    """Retorna uso percentual da RAM"""
    try:
        with open('/proc/meminfo', 'r') as f:
            lines = f.readlines()
            total_kb = int(lines[0].split()[1])
            available_kb = int(lines[2].split()[1])
            return int(100 * (1 - available_kb / total_kb))
    except:
        return 0


def set_game_mode(enable=True):
    """Ativa ou desativa game mode (CPU performance)"""
    if enable:
        try:
            for cpu in Path('/sys/devices/system/cpu').glob('cpu*/cpufreq/scaling_governor'):
                with open(cpu, 'w') as f:
                    f.write('performance')
            return True
        except Exception as e:
            print(f"[SYSTEM] Erro ao ativar game mode: {e}")
            return False
    else:
        try:
            for cpu in Path('/sys/devices/system/cpu').glob('cpu*/cpufreq/scaling_governor'):
                with open(cpu, 'w') as f:
                    f.write('powersave')
            return True
        except Exception as e:
            print(f"[SYSTEM] Erro ao desativar game mode: {e}")
            return False


def set_cpu_affinity(cores="0-3"):
    """Define afinidade de CPU para o processo atual"""
    try:
        os.sched_setaffinity(0, {int(c) for c in cores.split('-')})
        return True
    except:
        return False
