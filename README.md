# EMU-GPU Toolkit v2.1

**GPU via CPU + Tradutor de .exe — Interface Grafica Nativa**

Toolkit experimental que transforma seu processador (CPU) em uma placa de video virtual e executa jogos `.exe` do Windows no Ubuntu. Feito especialmente para quem tem um **CPU potente mas GPU fraca** — como o **Intel HD Graphics 3000**.

**NOVO na v2.1:** Campo de texto editavel para colar caminho de outros HDs, escaner de pasta inteira, e limpeza automatica da v1.0.

---

## Seu Hardware — i7-2760QM

| Componente | Especificacao |
|-----------|---------------|
| CPU | Intel Core i7-2760QM (4 cores / 8 threads) |
| GPU | Intel HD Graphics 3000 |

**O i7-2760QM e excelente para emulacao GPU!** Com 8 threads, renderiza graficos 3D por software via LLVMpipe/Lavapipe.

---

## Interface Grafica — Tudo Visual, Sem Comandos!

A v2.0+ traz uma **interface grafica completa** em tkinter. Tudo por cliques:

- Dashboard com status do sistema
- Biblioteca de jogos com botao **JOGAR**
- **Campo de texto editavel** — cole o caminho de qualquer HD (`/media/dragonscp/...`)
- **Escaner de pasta** — acha todos os .exe de uma vez
- Selecao visual de perfil de performance
- Sliders para FPS e resolucao

---

## Instalacao Rapida

### Se ja tem a v1.0 instalada:

```bash
cd ~/projects
git pull origin main
chmod +x install_gui.sh
./install_gui.sh
```

O instalador v2.1 **limpa a v1.0 automaticamente**!

### Instalacao nova:

```bash
cd ~/Downloads
git clone https://github.com/DragonBRX/projects.git
cd projects
chmod +x install_gui.sh
./install_gui.sh
```

---

## Como Usar

### Adicionar Jogo de Outro HD (Colar Caminho)

1. Abra o EMU-GPU Toolkit pelo **Menu de Aplicativos**
2. Clique em **"Adicionar Jogo"**
3. No campo de texto, **COLE** o caminho completo:
   ```
   /media/dragonscp/Novo volume/jogos/meu_jogo.exe
   ```
   Ou clique em **"Procurar..."** para navegar
4. Escolha o nome, perfil, FPS e resolucao
5. **"SALVAR E ADICIONAR"**

### Escanear Pasta Inteira

Clique em **"+ Procurar todos os .exe numa pasta"** e selecione uma pasta — o app acha **todos** os jogos automaticamente!

### Jogar

Va em **"Meus Jogos"** e clique no botao **VERDE "JOGAR"**.

---

## Como Funciona

| Tecnologia | Funcao |
|-----------|--------|
| **LLVMpipe** | OpenGL 4.5 renderizado pela CPU |
| **Lavapipe** | Vulkan 1.3 por software |
| **Zink** | Converte OpenGL → Vulkan |
| **DXVK** | DirectX 9/10/11 → Vulkan |
| **Wine** | Executa .exe no Linux |

---

## O que Roda no i7-2760QM

| Categoria | Jogos |
|-----------|-------|
| **Roda bem** | Stardew Valley, Terraria, Hollow Knight, Celeste |
| **Provavelmente roda** | Minecraft, Portal 1/2, Half-Life 2, GTA SA |
| **Talvez a 30 FPS / 720p** | Skyrim (2011), Fallout 3/NV, emuladores PS2 |

---

## Limpar Versao Antiga (v1.0)

Se a v1.0 ainda esta instalada, rode:

```bash
cd ~/projects
bash cleanup.sh
```

Isso remove todos os arquivos antigos, aliases do .bashrc e atalhos obsoletos.

---

## Estrutura

```
projects/
├── app/
│   ├── emu_gpu_gui.py      # Aplicativo GUI principal (v2.1)
│   └── launcher.sh         # Script de execucao
├── cleanup.sh              # Limpa v1.0
├── install_gui.sh          # Instalador automatico v2.1
├── config/
│   └── lvp_icd.x86_64.json # Config Vulkan
├── scripts/                # Scripts auxiliares
├── docs/
│   ├── README.md           # Documentacao completa
│   └── icon.png            # Icone do app
└── README.md               # Este arquivo
```

---

*Powered by Mesa LLVMpipe/Lavapipe + Wine + DXVK*
