---
name: auditoria-app-tkinter
description: Audita um app desktop em Python/Tkinter (código, arquitetura, performance e UX) a partir da pasta do projeto e entrega um relatório priorizado com evidências e correções. Use quando pedirem para auditar, revisar ou avaliar um sistema feito em Tkinter, ttk, ttkbootstrap ou customtkinter.
---

# Auditoria de App Desktop Python/Tkinter

Auditoria genérica e reutilizável para qualquer sistema feito em Python com Tkinter/ttk
(inclusive ttkbootstrap e customtkinter). Cobre quatro frentes: **código**, **arquitetura**,
**performance** e **UX**. O resultado é um relatório priorizado, em português, em que cada
problema traz evidência (arquivo:linha ou medição), impacto, correção sugerida e esforço.

## Regras gerais

- **Somente leitura.** Não altere código durante a auditoria. Correções só depois, e só se o usuário pedir.
- **Evidência sempre.** Nenhum achado sem arquivo:linha, saída de comando ou medição. Suposições vão marcadas como "a verificar".
- **Rode, não adivinhe.** Use as ferramentas abaixo e cite os resultados reais.
- **Agrupe repetições.** Ex.: "9 callbacks sem tratamento de erro" com 2 ou 3 exemplos.
- **Proporcionalidade.** Ajuste a severidade ao porte e ao uso do sistema (uso pessoal, equipe pequena, clientes).
- **Dados do usuário.** Nunca abra nem cite o conteúdo de `.env`, bancos de dados, planilhas ou arquivos com dados reais. Basta registrar que existem e como são acessados.

## Passo 0 — Acesso ao projeto

Descubra onde está o código e trabalhe a partir dali:
- **Claude Code** aberto na pasta do projeto: trabalhe direto no diretório atual.
- **App do Claude com acesso a pastas do computador:** peça acesso **só à pasta do projeto**, não à home inteira.
- **Sem acesso a pastas:** peça ao usuário um `.zip` só do código, sem `venv`, bancos de dados ou planilhas com dados reais.

Ignore sempre `venv`, `.venv`, `__pycache__`, `build`, `dist`, `.git`, `*.db`, `*.sqlite` e planilhas com dados.

## Passo 1 — Reconhecimento

Mapeie e anote:
- **Versão do Python e dependências:** `requirements.txt`/`pyproject.toml` (versões fixadas?), libs de UI (tk puro, ttk, ttkbootstrap, customtkinter), dados (sqlite3, pandas, openpyxl, SQLAlchemy), relatórios (reportlab, fpdf).
- **Ponto de entrada:** `main.py`/`app.py`, presença de `if __name__ == "__main__":`.
- **Estrutura:** árvore até 3 níveis; quantas janelas/telas (Tk, Toplevel, Frames); onde ficam a lógica de negócio e o acesso a dados.
- **Tamanho:** linhas por arquivo (`wc -l`) e os 10 maiores arquivos e funções.
- **Persistência:** onde e como os dados são salvos (SQLite, JSON, CSV, Excel, API).
- **Distribuição:** PyInstaller/auto-py-to-exe (`.spec`), instalador, sistema operacional alvo.
- **Objetivo e usuários:** pergunte em uma frase, se não estiver claro.

Escreva um resumo de 5 a 8 linhas do que o sistema é antes de seguir.

## Passo 2 — Ferramentas automáticas

Instale num ambiente isolado e rode (registre o comando e a saída resumida):
- `ruff check .`: erros, imports não usados, `except:` genérico, `from tkinter import *`
- `ruff check --select C901,PLR0912,PLR0915 .` ou `radon cc -s -n C .`: funções complexas demais
- `vulture .`: código morto
- `mypy .` (modo leniente), só se houver type hints
- `pytest`, se houver testes; registre se não houver nenhum
- `python -X importtime main.py 2> importtime.log` (com display virtual, ver abaixo): o que deixa a abertura lenta
- `pip list --outdated` / `pip-audit`: dependências velhas ou com falhas conhecidas

Se o app precisar de display e não houver um (Linux sem interface), use `xvfb-run -a python main.py` para verificar se abre sem erros (encerre com timeout). Falhas de ambiente são registradas, não tratadas como bug do código.

## Passo 3 — Código

- **Erros e exceções:** `except:` ou `except Exception: pass` que engolem erros; callbacks sem tratamento (no Tkinter a exceção vai para o console e o usuário não vê nada); ausência de `report_callback_exception` ou de log em arquivo.
- **Bugs típicos de Tkinter:**
  - `PhotoImage` sem referência guardada (a imagem some por garbage collection)
  - `command=funcao()` em vez de `command=funcao` (executa na criação)
  - lambdas em loop capturando a variável errada (`lambda: f(i)` em vez de `lambda i=i: f(i)`)
  - `StringVar`/`IntVar` criadas antes do `Tk()` ou sem referência
  - `.get()` de `Entry` convertido para `int`/`float` sem validação (quebra com vírgula decimal ou campo vazio)
  - múltiplas instâncias de `Tk()` em vez de `Toplevel`
- **Python em geral:** argumentos padrão mutáveis, variáveis globais modificadas em vários lugares, arquivos/conexões abertos sem `with`, caminhos relativos ao diretório atual (quebram ao rodar de outro lugar ou empacotado).
- **Legibilidade:** funções que montam a tela inteira em centenas de linhas, nomes como `e1`, `b2`, `frame3`, números mágicos de pixels e cores espalhados, código comentado, `print` de debug.
- **Duplicação:** telas de cadastro copiadas e coladas, validações repetidas, SQL repetido.
- **Testes:** quais regras de negócio críticas não têm teste (e se dão para testar sem abrir a interface).

## Passo 4 — Arquitetura

- **Separação UI × lógica × dados:** regra de negócio e SQL dentro de callbacks de botão? O ideal é pelo menos 3 camadas (telas → serviços/regras → repositório de dados), no estilo MVC ou MVP.
- **Organização das telas:** cada tela como classe (`ttk.Frame`/`Toplevel`) ou tudo em funções soltas no módulo principal? Como a navegação entre telas funciona?
- **Estado:** estado global em variáveis de módulo, widgets acessados de outras telas diretamente, dados duplicados entre telas.
- **Acesso a dados:** conexão aberta a cada operação vs. gerenciada; SQL montado com f-string/concatenação (use parâmetros `?`); transações e `commit` faltando; ausência de backup; esquema criado ou migrado de forma improvisada.
- **Configuração:** caminhos, credenciais e parâmetros fixos no código; falta de um módulo de configuração.
- **Recursos e caminhos:** ícones e arquivos localizados via `__file__`/`sys._MEIPASS` (necessário no PyInstaller)? Dados do usuário gravados na pasta do executável em vez de AppData ou home?
- **Evolução:** quão difícil é adicionar uma tela ou um campo novo? Aponte o gargalo.

Se ajudar, desenhe um diagrama simples de módulos e do fluxo de dados encontrado.

## Passo 5 — Performance

- **Travamento da interface (o problema nº 1 em Tkinter):** callbacks que fazem trabalho demorado (consulta grande, leitura de Excel, requisição HTTP, geração de PDF, `time.sleep`) direto no mainloop deixam a janela "Não respondendo". Correção: `threading`/`concurrent.futures` + `after()` para devolver o resultado.
- **Thread-safety:** widgets atualizados de dentro de threads (o Tkinter não é thread-safe). Deve usar `queue.Queue` + `after()` ou `event_generate`.
- **Anti-padrões de loop:** `root.update()` dentro de `while`, `after()` em laço que nunca é cancelado, polling agressivo.
- **Listas e tabelas:** `Treeview`/`Listbox` com milhares de linhas recriados por inteiro a cada mudança; falta de paginação ou filtro no banco (filtrar em Python depois de `SELECT *`).
- **Dados:** consultas N+1, falta de índices em colunas filtradas, planilhas relidas a cada clique, pandas carregado só para operações simples.
- **Abertura do app:** tempo de inicialização (`-X importtime`), imports pesados no topo que poderiam ser tardios, telas todas criadas no início sem necessidade.
- **Memória:** `Toplevel` e widgets criados repetidamente sem `destroy()`, imagens recarregadas a cada abertura de tela.
- **Medição:** quando der para isolar a lógica, use `cProfile`/`timeit` nas funções suspeitas e registre os tempos. Deixe claro o que é medido e o que é estimado.

## Passo 6 — UX

Se possível, abra o app e tire capturas das telas principais (em Linux sem interface: `xvfb-run` + `import -window root tela.png`; ou peça ao usuário prints das telas). Avalie:
- **Layout e redimensionamento:** `pack` e `grid` misturados no mesmo container (pode travar o app); `grid` sem `columnconfigure/rowconfigure(weight=...)` e `sticky`; janela sem `minsize`; posições fixas com `place`; telas que cortam em resoluções menores.
- **Escala e nitidez:** no Windows, falta de DPI awareness deixa tudo borrado; fontes fixas em pixels.
- **Consistência visual:** mistura de widgets `tk` e `ttk`, cores, fontes e espaçamentos diferentes entre telas, falta de tema.
- **Teclado:** ordem do Tab lógica, Enter para confirmar, Esc para fechar diálogos, foco inicial no primeiro campo, atalhos nas ações frequentes.
- **Formulários:** validação (`validatecommand` ou na hora de salvar) com mensagem clara indicando o campo; formatos brasileiros (vírgula decimal, datas dd/mm/aaaa, CPF/CNPJ, moeda); campos que não são limpos ou mantidos de forma coerente após salvar.
- **Feedback:** confirmação após salvar ou excluir; `askyesno` antes de ações destrutivas; barra de progresso, cursor de espera ou barra de status em operações demoradas; mensagens de erro compreensíveis em vez de tracebacks.
- **Janelas:** diálogos modais com `transient` + `grab_set`; janelas que abrem duplicadas ao clicar duas vezes; janelas que abrem fora da tela ou atrás da principal; título e ícone definidos.
- **Fluxo principal:** percorra a tarefa mais comum do sistema e aponte atritos (cliques demais, telas desnecessárias, dados redigitados).

## Passo 7 — Priorização

| Severidade | Critério |
|---|---|
| **Crítico** | Perde ou corrompe dados, trava o app ou impede uma tarefa principal |
| **Alto** | Bug provável, interface congelando, risco alto de manutenção |
| **Médio** | Dívida técnica relevante, atrito perceptível de UX |
| **Baixo** | Polimento, higiene, estilo |

Esforço: **P** (< 1h), **M** (meio dia), **G** (> 1 dia).
Ordene por severidade e depois pelo menor esforço. Destaque os "quick wins" (severidade alta com esforço P).

## Passo 8 — Relatório

Entregue como documento (não como resposta longa no chat), com esta estrutura:

1. **Resumo executivo**: 5 a 8 linhas: o que é o sistema, estado geral e os 3 problemas mais importantes.
2. **Notas por frente** (0–10, com uma frase de justificativa cada): Código · Arquitetura · Performance · UX.
3. **Quick wins**: lista curta do que fazer primeiro.
4. **Achados detalhados**, por frente. Para cada um:
   - Título curto · Severidade · Esforço
   - Evidência (arquivo:linha, trecho mínimo, captura de tela ou medição)
   - Por que importa
   - Como corrigir (concreto, com exemplo curto de código antes → depois quando ajudar)
5. **Pontos fortes**: o que está bem feito e deve ser mantido.
6. **Plano de ação**: roteiro em 3 ondas (agora / próximas semanas / depois), incluindo uma proposta de estrutura de pastas se a arquitetura precisar ser reorganizada.
7. **Anexo**: comandos executados, versões, o que não foi possível verificar e por quê.

No chat, responda só com o resumo executivo e as notas, e entregue o documento.
Termine oferecendo começar pelos quick wins.
