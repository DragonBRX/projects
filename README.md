# EMU-GPU Toolkit v2.0

**GPU via CPU + Traducao Propria de .exe para Ubuntu/Linux**

Um launcher completo que transforma sua CPU em uma placa de video virtual e executa jogos `.exe` do Windows no Ubuntu — **sem depender do Wine como aplicativo**. Usa codigo-fonte open-source de DXVK, VKD3D-Proton, FAudio e outros projetos para criar uma camada de traducao integrada.

---

## NOVO na v2.0

- **Interface GTK4/libadwaita** — design moderno estilo Steam/Lutris, nativo do Ubuntu
- **Traducao Propria** — usa DXVK, VKD3D, FAudio via codigo-fonte open-source, nao apenas chama `wine`
- **Explorador Nativo** — usa Nautilus (gerenciador de arquivos do Ubuntu) para navegar por todos os HDs
- **File Chooser Portal** — file picker nativo do GTK4 que integra com o sistema
- **Ferramentas Experimentais** — FSR, Frame Generation, Shader Cache
- **Analise de PE** — escaneia executaveis e detecta dependencias automaticamente

---

## Seu Hardware — i7-2760QM

| Componente | Especificacao |
|------------|--------------|
| CPU | Intel Core i7-2760QM (4 cores / 8 threads) |
| GPU | Intel HD Graphics 3000 |

O i7-2760QM e excelente para emulacao GPU! Com 8 threads, renderiza graficos 3D por software via LLVMpipe/Lavapipe.

---

## Interface Grafica — Moderna e Nativa

A v2.0 traz uma interface **GTK4/libadwaita** profissional:

- **Dashboard** com status do sistema em tempo real
- **Biblioteca de jogos** com cards estilo Steam
- **Adicionar jogo** com explorador Nautilus nativo
- **Configuracoes** de tradutores, renderizadores e otimizacoes
- **Ferramentas Experimentais** para usuarios avancados
- **File chooser nativo** que acessa todos os HDs em `/media/`

### Explorador de Arquivos

A v2.0 usa o **Nautilus** (explorador de arquivos padrao do Ubuntu):
- Clique em "Abrir Nautilus..." para navegar normalmente
- Acesse todos os seus HDs, pendrives, pastas de rede
- Copie o caminho completo (Ctrl+C) e cole no launcher

Tambem disponivel o **file chooser nativo do GTK4** que usa o portal do sistema.

---

## Renderizacao por CPU

### Modos Disponiveis

| Modo | Nome | Para que serve |
|------|------|---------------|
| `llvmpipe` | OpenGL por CPU | Jogos 2D e leves. Maxima compatibilidade. |
| `lavapipe` | Vulkan por CPU | Jogos com DXVK. DirectX 9/10/11 via Vulkan. |
| `swrender-full` | Render Completo | OpenGL + Vulkan + Zink. Melhor resultado geral. |

### Recomendado para i7-2760QM

- **Resolucao:** 1280x720
- **FPS Limit:** 30 (para jogos 3D), 60 (para jogos 2D)
- **Renderer:** Render Completo (swrender-full)

---

## Camada de Traducao

A v2.0 usa uma **camada de traducao propria** baseada em codigo-fonte open-source:

| Modulo | Funcao | Origem |
|--------|--------|--------|
| **DXVK** | DirectX 9/10/11 -> Vulkan | [doitsujin/dxvk](https://github.com/doitsujin/dxvk) |
| **VKD3D-Proton** | DirectX 12 -> Vulkan | [HansKristian-Work/vkd3d-proton](https://github.com/HansKristian-Work/vkd3d-proton) |
| **WineD3D** | DirectX -> OpenGL | [WineHQ](https://gitlab.winehq.org/wine/wine) |
| **FAudio** | XAudio2 reimplementacao | [FNA-XNA/FAudio](https://github.com/FNA-XNA/FAudio) |

**Diferente da v1:** Nao chamamos `wine jogo.exe`. Carregamos as DLLs de traducao diretamente e usamos o Wine apenas como backend de bibliotecas.

---

## Instalacao Rapida

```bash
# Clone o repositorio
git clone https://github.com/DragonBRX/projects.git
cd projects

# Rode o instalador
bash install.sh
```

O instalador configura tudo automaticamente:
1. GTK4, libadwaita, Nautilus
2. Drivers Mesa LLVMpipe/Lavapipe
3. Modulos de traducao (DXVK, VKD3D, FAudio)
4. Wine (apenas bibliotecas)
5. EMU-GPU Toolkit v2.0

## Uso

```bash
# Iniciar interface grafica
emu-gpu

# Ou diretamente
cd ~/.emu-gpu/app && python3 main.py
```

## Atalhos

| Comando | Funcao |
|---------|--------|
| `emu-gpu` | Interface grafica principal |
| `swrender <programa>` | Render completo por CPU |
| `llvmpipe <programa>` | OpenGL por software |
| `lavapipe <programa>` | Vulkan por software |
| `game-mode` | Ativa performance maxima da CPU |

---

## Estrutura do Projeto v2.0

```
projects/
├── app/
│   ├── main.py              # Entry point (GTK4/libadwaita)
│   ├── window.py            # Janela principal
│   ├── launcher.sh          # Script de lancamento
│   └── core/
│       ├── config.py        # Configuracoes e constantes
│       ├── system.py        # Deteccao de hardware
│       └── translator.py    # Camada de traducao propria
├── install.sh               # Instalador principal
└── README.md
```

---

## Jogos Compativeis

Jogos que devem rodar bem no i7-2760QM:

- Stardew Valley (2D)
- Terraria (2D)
- Hollow Knight (2D)
- Celeste (2D)
- Minecraft com OptiFine (3D leve)
- Portal 1/2 (3D/Source)
- Half-Life 2 (3D/Source)
- GTA San Andreas (3D)
- Fallout 3/New Vegas (3D)
- Skyrim (2011) (3D)

---

## Requisitos

- Ubuntu 22.04+ (ou derivado)
- CPU x86_64 com 4+ cores (8+ threads recomendado)
- 4GB+ RAM (8GB recomendado)
- GTK4/libadwaita
- Vulkan drivers (Mesa)

---

## Creditos

- **DXVK** — [doitsujin](https://github.com/doitsujin/dxvk)
- **VKD3D-Proton** — [HansKristian-Work](https://github.com/HansKristian-Work/vkd3d-proton)
- **FAudio** — [FNA-XNA](https://github.com/FNA-XNA/FAudio)
- **Wine** — [WineHQ](https://www.winehq.org/)
- **Proton** — [ValveSoftware](https://github.com/ValveSoftware/Proton)
- **Mesa** — [mesa3d.org](https://www.mesa3d.org/)

---

## Licenca

Projeto experimental para uso pessoal. Componentes de terceiros mantem suas respectivas licencas (MIT, LGPL, etc.).

---

**Feito para CPUs potentes com GPUs fracas.**
