# ✈ WingLabs Studio

**Gerador e Otimizador Aerodinâmico de Asas NACA 2D/3D** com pipeline autônoma integrada entre **XFOIL 6.99** (análise aerodinâmica 2D) e **PicoGK / LEAP71 ShapeKernel (.NET 9)** (modelagem volumétrica 3D para manufatura aditiva e CAD).

---

## Visão Geral

O **WingLabs Studio** automatiza o ciclo completo de seleção aerodinâmica e modelagem geométrica de asas baseadas em perfis **NACA de 4 dígitos**:

1. **Módulo 1 — Análise e Otimização 2D (Python + XFOIL):**
   - Calcula propriedades atmosféricas padrão **ISA** (densidade $\rho$, viscosidade dinâmica $\mu$, número de Reynolds e Mach) a partir da altitude, velocidade e corda raiz.
   - Suporta dois modos de otimização:
     - **Carga / Peso (`payload`):** calcula o $C_{L,\text{mín}}$ necessário para sustentar a massa informada na área alar trapezoidal e maximiza $C_L / C_D$.
     - **CL Alvo Fixo (`target_cl`):** busca o melhor ponto da polar dentro da tolerância $\pm \Delta C_L$.
   - Executa simulações paralelas (`ThreadPoolExecutor`) no **XFOIL** e ranqueia os **Top 4** aerofólios candidatos.
   - Exporta coordenadas e relatórios em `.dat`, `.svg`, `.json` e `.png`.

2. **Módulo 2 — Preview & Geração Volumétrica 3D (NumPy + PicoGK C#):**
   - Visualização **3D em tempo real** da asa na interface gráfica (envergadura, corda raiz/ponta, enflechamento, torção geométrica na ponta e diedro) usando malha vetorizada em NumPy.
   - Integração autônoma via JSON (`wing3d_config.json`) com o projeto C# (`3D Generator/winglabs.csproj`) para geração de malha sólida **`.stl`** baseada em *voxels* via **PicoGK**.

---

## Estrutura do Projeto

```text
WingLabs/
├── main.py                      # Ponto de entrada unificado (GUI por padrão ou --cli)
├── pyproject.toml               # Metadados do projeto e configuração de lint
├── requirements.txt             # Dependências Python fixadas
├── xfoil.exe                    # Executável do solver aerodinâmico XFOIL
├── README.md                    # Documentação principal
├── LICENSE                      # Licença do projeto
│
├── winglabs/                    # Pacote principal Python
│   ├── __init__.py
│   ├── __main__.py              # Permite execução via `python -m winglabs`
│   ├── paths.py                 # Resolução centralizada de caminhos (dev e PyInstaller)
│   ├── cli.py                   # Interface de linha de comando (CLI)
│   ├── core/
│   │   ├── environment.py       # Atmosfera padrão ISA, área alar e CL requerido
│   │   ├── naca.py              # Gerador matemático de perfis NACA 4 dígitos
│   │   └── pipeline.py          # Orquestração do Módulo 2 (PicoGK) e malha 3D preview
│   ├── aero/
│   │   ├── xfoil_engine.py      # Wrapper XFOIL, parser de polares e exportadores 2D
│   │   ├── script_sender.py     # Gerador de scripts de comando para o XFOIL
│   │   ├── naca_tester.py       # Execução unitária e filtros físicos por Reynolds
│   │   └── optimizer.py         # Busca paralela Multi-Thread e ranking Top 4
│   └── ui/
│       └── app.py               # Interface desktop Tkinter (Dark Aerospace CAD)
│
├── tests/
│   └── test_winglabs.py         # Suíte de testes unitários e de layout/fluxo da UI
│
├── 3D Generator/                # Módulo 2 em C# (.NET 9 + PicoGK + LEAP71 ShapeKernel)
│   ├── Program.cs
│   ├── winglabs.csproj
│   ├── src/
│   └── LEAP71_ShapeKernel/
│
├── XFOIL6.99/                   # Distribuição de referência do XFOIL 6.99
└── output/                      # Diretório padrão para arquivos exportados (.dat, .svg, .json, .stl)
```

---

## Pré-requisitos

- **Sistema Operacional:** Windows 10/11 (necessário para `xfoil.exe` e renderização DPI-aware).
- **Python:** 3.11 ou superior.
- **XFOIL:** `xfoil.exe` presente na raiz do repositório (`WingLabs/xfoil.exe`).
- **.NET SDK 9.0** *(opcional para uso 2D, obrigatório para geração `.stl` via Módulo 2 PicoGK)*.

---

## Instalação

```powershell
# 1. Crie e ative o ambiente virtual
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Instale as dependências Python
pip install -r requirements.txt
```

---

## Como Executar

### Interface Gráfica (Padrão)

```powershell
python main.py
```

Ou diretamente como módulo Python:

```powershell
python -m winglabs
```

**Atalhos na GUI:**
- `Ctrl + Enter`: inicia a otimização aerodinâmica 2D.
- `Esc`: cancela a otimização em andamento.
- `Tab + Enter` / clique nos cards **Top 4**: alterna em tempo real entre os 4 melhores perfis nos gráficos 2D e 3D.

### Modo Terminal (CLI)

```powershell
python main.py --cli
```

---

## Testes Automatizados

A suíte em `tests/test_winglabs.py` valida a geração matemática NACA, cálculos atmosféricos ISA, seleção de polares, filtros físicos, exportadores, malha 3D vetorizada e integridade geométrica da interface:

```powershell
python -m unittest discover -s tests -v
```

---

## Licença

Consulte o arquivo [LICENSE](LICENSE) para detalhes sobre termos de uso e distribuição.
