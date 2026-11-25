# 4. Resultados e Discussão — WingLabs

O desenvolvimento do sistema **WingLabs** resultou em uma plataforma integrada capaz de automatizar o ciclo completo de projeto preliminar de asas, unindo a seleção aerodinâmica bidimensional (via XFOIL) à geração paramétrica de modelos sólidos tridimensionais prontos para manufatura aditiva ou análise estrutural (formato `.stl`).

---

## 4.1 Desempenho da Pipeline de Otimização Aerodinâmica 2D

A pipeline de otimização 2D demonstrou capacidade de calcular dinamicamente as condições atmosféricas pelo modelo ISA (*International Standard Atmosphere*), executar varreduras paralelas (*Grid Search* via `ThreadPoolExecutor`) sobre famílias de perfis NACA de 4 dígitos e filtrar automaticamente soluções não físicas com base em limites de arrasto mínimo ($C_{D,\min}$) e eficiência máxima esperados para o número de Reynolds ($Re$) calculado.

Para validar o comportamento do otimizador em diferentes escalas de operação, foram analisados ensaios no modo de seleção por carga útil (*payload*), divididos entre regime de **baixo Reynolds** (escala reduzida/protótipo) e **alto Reynolds** (escala real/VANT). Os resultados aerodinâmicos obtidos estão consolidados na Tabela 1.

**Tabela 1 — Resultados aerodinâmicos obtidos pela pipeline 2D (XFOIL)**

| Perfil Selecionado | Altitude (m) | Velocidade (m/s) | Corda Raiz (m) | Reynolds ($Re$) | $\alpha_{\text{opt}}$ ($^\circ$) | $C_L$ | $C_D$ | Eficiência ($C_L/C_D$) | Sustentação (kgf) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **NACA 3312** | 1500 | 42,0 | 1,63 | $4,16 \times 10^6$ | 5,0 | 0,9016 | 0,00606 | **148,78** | 601,50 |
| **NACA 4710** | 1000 | 42,0 | 1,63 | $4,33 \times 10^6$ | 0,0 | 0,6367 | 0,00452 | **140,86** | 446,27 |
| **NACA 3510** | 1500 | 60,0 | 0,12 | $4,37 \times 10^5$ | 0,0 | 0,3793 | 0,00633 | **59,92** | 1,10 |
| **NACA 5310** | 1500 | 60,0 | 0,12 | $4,37 \times 10^5$ | 0,0 | 0,5367 | 0,00951 | **56,44** | 1,56 |

Observa-se coerência física direta nos resultados:
- Nos ensaios de **escala reduzida** ($S = 0,015\text{ m}^2$, carga alvo de $0,5\text{ kg}$ e $Re \approx 4,37 \times 10^5$), os perfis **NACA 3510** e **NACA 5310** apresentaram eficiências aerodinâmicas entre $56,44$ e $59,92$, compatíveis com o maior efeito viscoso em baixos números de Reynolds, atendendo ao requisito de sustentação da missão.
- Nos ensaios de **escala real** ($S = 7,0104\text{ m}^2$, carga alvo de $120\text{ kg}$ e $Re > 4,1 \times 10^6$), o sistema selecionou perfis de maior eficiência, como o **NACA 4710** ($L/D = 140,86$) e o **NACA 3312** ($L/D = 148,78$), refletindo a redução do coeficiente de arrasto ($C_D$ entre $0,00452$ e $0,00606$) em altos números de Reynolds.

Ao final de cada execução, o módulo exportou automaticamente as coordenadas normalizadas (`.dat`), o contorno vetorial (`.svg`) e os metadados completos da simulação (`.json`).

---

## 4.2 Desempenho da Pipeline de Geração Paramétrica 3D

A integração autônoma entre o ambiente Python e o motor geométrico em C# (`.NET` / **PicoGK** + **LEAP71_ShapeKernel**) converteu diretamente os perfis 2D selecionados em malhas tridimensionais fechadas a partir do arquivo de configuração `wing3d_config.json`. No ensaio de referência em escala real (envergadura de $5080\text{ mm}$, corda na raiz de $1630\text{ mm}$, corda na ponta de $1130\text{ mm}$, torção de $-1,0^\circ$, diedro de $1,0^\circ$, passo de seção de $20,0\text{ mm}$ e voxel de $5,0\text{ mm}$), o gerador construiu os *lofts* intermediários, aplicou o fechamento hermético das extremidades (*caps*) e exportou malhas estanques (`.stl`) de **`457 KB`** (escala reduzida) a **`12,95 MB`** (escala real).

---

## 4.3 Avaliação de Tempo Operacional e Ganho de Produtividade

Para quantificar o impacto da automação sobre o tempo de projeto, foram realizados ensaios cronometrados ponta a ponta:
1. **Ensaio com configuração padrão ampliada**: $210$ perfis NACA avaliados no XFOIL em $4$ *threads* paralelas ($240$ painéis, $100$ iterações, $\alpha \in [-2^\circ, 12^\circ]$ com passo de $1^\circ$), seguido da geração automática da asa 3D de $12,95\text{ MB}$.
2. **Estudo de caso com parâmetros de alta discretização da GUI** (detalhado na Seção 4.4): $84$ perfis NACA em $11$ *threads* paralelas ($300$ painéis, $200$ iterações, $\alpha \in [0^\circ, 10^\circ]$ com passo de $0,5^\circ$), seguido da geração da malha 3D.

**Tabela 2 — Tempos reais medidos na execução completa das pipelines**

| Cenário / Etapa | Escopo Executado | Tempo Medido | Observações |
| :--- | :--- | :---: | :--- |
| **Varredura Padrão (2D)** | 210 perfis no XFOIL (4 *threads*, 240 painéis, 100 iter.) | **183,19 s** (~3 min 03 s) | Média de **0,87 s/perfil** |
| **Geração 3D Padrão** | Leitura `.dat`/JSON, *lofting*, *caps*, voxelização e `.stl` | **~8,00 s** | Malha estanque de 12,95 MB |
| **Total Padrão (2D → 3D)** | Fluxo autônomo completo (210 perfis → STL) | **~191,19 s (~3 min 11 s)** | Sem intervenção manual |
| **Estudo de Caso GUI (2D)** | 84 perfis no XFOIL (11 *threads*, 300 painéis, 200 iter.) | **121,12 s** (~2 min 01 s) | Malha refinada (300 painéis, $\Delta\alpha = 0,5^\circ$) |
| **Estudo de Caso GUI (3D)** | Geração da asa NACA 3312 em escala real (`.stl`) | **8,61 s** | Malha estanque de 12,95 MB (12.954.084 bytes) |
| **Total Caso GUI (2D → 3D)** | Fluxo autônomo completo (84 perfis → STL) | **129,73 s (~2 min 10 s)** | Redução expressiva frente ao fluxo manual |

Os resultados cronometrados comprovam uma expressiva redução no tempo operacional em comparação ao fluxo de trabalho manual tradicional. Em um processo convencional não automatizado, a avaliação individual de dezenas ou centenas de perfis no XFOIL, a tabulação manual das polares para cálculo de eficiência ($C_L/C_D$), a importação de coordenadas em software CAD, a criação manual de planos de seção com afilamento, torção e diedro e a exportação da malha demandariam diversas horas de operação sujeitas a erro humano. Com o **WingLabs**, todo o ciclo de seleção aerodinâmica e modelagem sólida tridimensional foi concluído de forma autônoma em **2 a 3 minutos**.

---

## 4.4 Estudo de Caso Específico: Configuração da Interface Gráfica

Como validação reprodutível dos resultados exibidos na interface gráfica (`WingLabsGUI`), executou-se o pipeline completo com os parâmetros exatos configurados pelo usuário para uma missão de carga útil em escala real.

### Parâmetros de Entrada Utilizados

- **Cenário de Voo (Módulo 1 — Carga / Peso)**:
  - Altitude: $1500\text{ m}$ ($\rho = 1,0581\text{ kg/m}^3$)
  - Velocidade: $42\text{ m/s}$ ($\text{Mach} = 0,1256$)
  - Massa / Carga Útil: $120\text{ kg}$
  - Área Alar ($S$): $7,0104\text{ m}^2$
  - Número de Reynolds ($Re$): $4.158.412$
  - $C_L$ mínimo requerido para sustentação: $0,1799$
- **Busca & XFOIL (Avançado)**:
  - Camber máximo: $6$ | Espessuras (%): `10, 12` ($84$ perfis NACA avaliados)
  - Intervalo de $\alpha$: $0^\circ$ a $10^\circ$ com passo de $0,5^\circ$ ($21$ ângulos por perfil)
  - Painéis XFOIL: $300$ | Iterações máximas: $200$ | Tolerância $C_L$: $\pm 0,5$ | *Threads*: $11$
- **Geometria 3D da Asa (Módulo 2)**:
  - Envergadura: $5080\text{ mm}$ | Corda raiz: $1630\text{ mm}$ | Corda ponta: $1130\text{ mm}$
  - Enflechamento: $0^\circ$ | Torção na ponta: $-1^\circ$ | Diedro: $1^\circ$
  - Tamanho alvo de seção: $20\text{ mm}$ | Resolução de voxel: $5\text{ mm}$

### Resultados Obtidos no Estudo de Caso

Dos $84$ perfis testados em paralelo com $11$ *threads*, o otimizador concluiu a varredura em **`121,12 s`**, selecionando os quatro melhores candidatos por eficiência aerodinâmica ($C_L/C_D$), listados na Tabela 3.

**Tabela 3 — Ranking dos 4 melhores perfis obtidos no estudo de caso**

| Posição | Perfil | $\alpha_{\text{opt}}$ ($^\circ$) | $C_L$ | $C_D$ | Eficiência ($C_L/C_D$) |
| :---: | :--- | :---: | :---: | :---: | :---: |
| **1º** | **NACA 3312** | 5,0 | 0,9016 | 0,00606 | **148,78** |
| **2º** | **NACA 4610** | 0,5 | 0,6275 | 0,00428 | **146,61** |
| **3º** | **NACA 4512** | 4,5 | 0,9836 | 0,00673 | **146,15** |
| **4º** | **NACA 3410** | 3,5 | 0,7482 | 0,00520 | **143,88** |

Em seguida, o perfil campeão (**NACA 3312**) foi automaticamente exportado para `.dat` e processado pelo **Módulo 2 (.NET C# / PicoGK)** em **`8,61 s`**, produzindo a malha tridimensional fechada (`.stl`) de **`12.954.084 bytes` (`12,95 MB`)**. O processo completo — da simulação aerodinâmica de alta resolução (300 painéis, 200 iterações) à geração do sólido 3D — foi concluído em **`129,73 s` (~2 min 10 s)**.
