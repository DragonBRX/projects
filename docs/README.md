# EMU-GPU Toolkit v1.0

**GPU via CPU + Tradutor de .exe para Ubuntu/Linux**

Um toolkit experimental que permite emular uma placa de vídeo usando o processador (CPU) e traduzir/executar arquivos `.exe` do Windows no Ubuntu. Ideal para notebooks e PCs com CPUs potentes mas GPUs fracas (como Intel HD Graphics 3000).

---

## Como Funciona

O seu processador tem **4 núcleos e 8 threads** — isso é poder de sobra para muitas tarefas! O problema é que a **Intel HD 3000** não consegue renderizar gráficos modernos. Este toolkit resolve isso:

### Emulação GPU via CPU

| Tecnologia | O que faz |
|------------|-----------|
| **LLVMpipe** | Transforma sua CPU em uma GPU OpenGL. Usa instruções SSE/AVX para renderizar gráficos 3D |
| **Lavapipe** | Implementa Vulkan 1.3 por software — permite rodar jogos DirectX 9/10/11/12 via DXVK/VKD3D |
| **Zink** | Converte chamadas OpenGL para Vulkan (que roda por software no Lavapipe) |
| **DXVK** | Traduz DirectX 9/10/11 → Vulkan (que vai para a CPU via Lavapipe) |
| **VKD3D** | Traduz DirectX 12 → Vulkan |

### Tradução de .exe

| Ferramenta | Função |
|------------|--------|
| **Wine** | Camada de compatibilidade Windows → Linux |
| **Winetricks** | Instala bibliotecas Windows (.NET, DirectX, etc.) |

---

## Requisitos

- **Sistema**: Ubuntu 20.04+ / Debian 11+ (64-bit)
- **CPU**: x86_64, 4+ cores/threads (o seu de 4C/8T é perfeito!)
- **RAM**: 4GB mínimo, 8GB+ recomendado
- **GPU**: Qualquer uma (a Intel 3000 serve como display, a CPU faz o trabalho pesado)

---

## Instalação Rápida

```bash
# 1. Baixar e extrair o toolkit
cd ~/Downloads
git clone <url-do-repositorio> emu-gpu-toolkit  # ou extrair o zip
cd emu-gpu-toolkit

# 2. Rodar o instalador
chmod +x install.sh
./install.sh

# 3. Reiniciar o terminal (ou source ~/.bashrc)
source ~/.bashrc
```

O instalador vai:
1. Instalar pacotes do sistema (Mesa, Vulkan, Wine, Python)
2. Configurar LLVMpipe e Lavapipe (GPU por software)
3. Baixar DXVK e VKD3D (tradução DirectX)
4. Instalar a ferramenta `emu-gpu`
5. Criar scripts de otimização

---

## Comandos Principais

### Ver status do sistema
```bash
emu-gpu status
```

### Rodar um jogo .exe com GPU via CPU
```bash
# Modo automático (recomendado)
emu-gpu run-cpu "/caminho/para/jogo.exe"

# Com limitador de FPS (reduz carga na CPU)
emu-gpu run-cpu --fps-limit 30 "/caminho/para/jogo.exe"

# Usar apenas OpenGL por software (para jogos antigos)
emu-gpu run-cpu --renderer llvmpipe "jogo.exe"

# Usar Vulkan por software (para jogos com DXVK)
emu-gpu run-cpu --renderer lavapipe "jogo.exe"

# Modo completo (OpenGL + Vulkan por software)
emu-gpu run-cpu --renderer swrender-full "jogo.exe"
```

### Benchmark de renderização
```bash
emu-gpu benchmark
```

### Instalar um jogo (setup.exe)
```bash
emu-gpu install ./setup.exe --name "Nome do Jogo"
```

### Rodar jogo instalado
```bash
emu-gpu play "Nome do Jogo"
```

### Analisar um .exe
```bash
emu-gpu translate "jogo.exe"
```

### Monitorar CPU em tempo real
```bash
emu-gpu monitor
```

---

## Scripts Rápidos

### quick-translate.sh
Roda qualquer .exe sem precisar instalar:

```bash
# Uso básico
./scripts/quick-translate.sh jogo.exe

# Com opções
./scripts/quick-translate.sh jogo.exe --opengl --fps 30
./scripts/quick-translate.sh jogo.exe --full --cores 2 --resolution 1280x720
```

### game-launcher.sh
Lançador avançado com mais controle:

```bash
./scripts/game-launcher.sh jogo.exe --renderer llvmpipe --fps-limit 30 --game-mode --hud
```

### Atualizar DXVK
```bash
./scripts/update-dxvk.sh --stable     # Versão estável (padrão)
./scripts/update-dxvk.sh --latest     # Última versão
./scripts/update-dxvk.sh --version 1.10.3
```

---

## Aliases Úteis (criados automaticamente)

```bash
# Ativar/desativar ambiente
source ~/.emu-gpu/activate      # Ativa GPU via CPU no shell atual
~/.emu-gpu/deactivate           # Desativa

# Renderização rápida
swrender programa           # Roda com renderização completa por software
llvmpipe programa           # Roda com OpenGL por CPU
lavapipe programa           # Roda com Vulkan por CPU

# Otimização da CPU
sudo game-mode              # Modo performance (clock máximo)
sudo powersave-mode         # Modo economia
```

---

## Renderizadores Disponíveis

| Renderizador | Tecnologia | Uso Ideal | Performance |
|-------------|------------|-----------|-------------|
| **llvmpipe** | OpenGL por CPU | Jogos antigos (DirectX 8/9), OpenGL nativo | ★★★☆☆ |
| **lavapipe** | Vulkan por CPU | Jogos com DXVK (DirectX 9/10/11) | ★★☆☆☆ |
| **swrender-full** | OpenGL+Vulkan+Zink | Todos os jogos (recomendado) | ★★★☆☆ |

### Qual escolher?

- **Jogos 2D/leves (Stardew Valley, Hollow Knight)**: `llvmpipe`
- **Jogos 3D médios (Skyrim, Fallout 3)**: `swrender-full`
- **Jogos modernos (com DXVK)**: `lavapipe` ou `swrender-full`

---

## Dicas de Performance

### 1. Limite de FPS
Sua CPU renderizando por software é poderosa, mas tem limites. Limite o FPS para ter fluidez:

```bash
emu-gpu run-cpu --fps-limit 30 jogo.exe     # Jogos pesados
emu-gpu run-cpu --fps-limit 60 jogo.exe     # Jogos médios
```

### 2. Resolução menor
Jogar em 720p (1280x720) ou até 900p ao invés de 1080p alivia MUITO a CPU:

```bash
# Configurar no jogo ou via argumentos
./scripts/quick-translate.sh jogo.exe --resolution 1280x720
```

### 3. Modo Game
Coloca a CPU em clock máximo:

```bash
sudo ~/.emu-gpu/scripts/cpu-governor-game.sh
```

### 4. Afinidade de CPU
Isola cores físicos para o jogo (automático no emu-gpu):

- Com 4C/8T: Cores 0,1,2,3 vão para o jogo; 4,5,6,7 para o sistema

### 5. Fechar programas
Feche navegador, Discord, etc. A CPU precisa de todo o poder disponível.

---

## Estrutura do Projeto

```
emu-gpu-toolkit/
├── install.sh              # Instalador principal
├── src/
│   └── emu_gpu.py          # Ferramenta CLI principal
├── scripts/
│   ├── game-launcher.sh    # Lançador avançado
│   ├── quick-translate.sh  # Tradução rápida de .exe
│   ├── update-dxvk.sh      # Atualizador de DXVK
│   ├── cpu-governor-game.sh     # Modo performance
│   ├── cpu-governor-powersave.sh # Modo economia
│   ├── cpu-affinity-launcher.sh  # Afinidade de CPU
│   ├── fps-limiter.sh            # Limitador de FPS
│   └── install-dxvk.sh           # Instala DXVK no prefixo
├── config/
│   ├── settings.json       # Configurações do usuário
│   └── lvp_icd.x86_64.json # Configuração Vulkan
└── docs/
    └── README.md           # Esta documentação
```

---

## Solução de Problemas

### "Vulkan não encontrado"
```bash
sudo apt install mesa-vulkan-drivers vulkan-tools
vulkaninfo --summary  # Verificar
```

### "Wine não encontrado"
```bash
sudo dpkg --add-architecture i386
sudo apt update
sudo apt install wine64 wine32
```

### "Jogo lento demais"
```bash
# Tente:
emu-gpu run-cpu --renderer llvmpipe --fps-limit 30 jogo.exe
```

### "Erro de DLL no Wine"
```bash
winetricks d3dx9 d3dx10 d3dx11  # Instalar DirectX
winetricks dotnet48              # Instalar .NET Framework
```

---

## Limitações Conhecidas

1. **Performance**: Renderização por CPU é ~10-50x mais lenta que GPU dedicada. Jogos muito pesados (Cyberpunk 2077, etc.) não vão rodar de forma jogável.

2. **Compatibilidade**: Nem todos os jogos funcionam. Jogos com DRM pesado (alguns Denuovo) podem não rodar.

3. **APIs gráficas**: OpenGL 4.5 e Vulkan 1.3 são suportados. DirectX 12 funciona via VKD3D mas é mais lento.

4. **Sua CPU**: 4C/8T é bom para jogos leves a médios. Não espere rodar AAA recentes.

---

## Jogos Testados (estimativa para 4C/8T + renderização por software)

| Jogo | Expectativa |
|------|-------------|
| Stardew Valley | Rodaria bem (2D leve) |
| Hollow Knight | Rodaria bem |
| Terraria | Rodaria bem |
| Minecraft (Java) | Rodaria (use OptiFine + limitar chunks) |
| Skyrim (2011) | Talvez jogável a 30 FPS em 720p |
| Fallout 3/NV | Provavelmente jogável a 30 FPS |
| GTA San Andreas | Rodaria bem |
| Portal 2 | Provavelmente jogável |
| Half-Life 2 | Rodaria bem |
| Jogos PS2/PSP (emuladores) | Rodaria bem no PCSX2/PPSSPP |

---

## Tecnologias Utilizadas

- [Mesa 3D](https://mesa3d.org/) — Drivers gráficos open source
- [LLVMpipe](https://docs.mesa3d.org/drivers/llvmpipe.html) — OpenGL por software
- [Lavapipe](https://docs.mesa3d.org/drivers/lavapipe.html) — Vulkan por software
- [Wine](https://www.winehq.org/) — Compatibilidade Windows
- [DXVK](https://github.com/doitsujin/dxvk) — DirectX → Vulkan
- [VKD3D-Proton](https://github.com/HansKristian-Work/vkd3d-proton) — DirectX 12 → Vulkan

---

## Licença

Projeto experimental — use por sua conta e risco. As tecnologias utilizadas são todas open source.

---

**Criado para quem tem CPU potente e GPU fraca — aproveite o poder do seu processador!**
