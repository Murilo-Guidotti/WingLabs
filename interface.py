# ============================================================
# NACA Wing Profile Generator — Interface Gráfica
# gui.py — arquivo separado do motor principal (main.py)
# ============================================================

# LAYOUT:
#   ┌──────────────────────────────────────────────────┐
#   │  painel_esq (inputs)  │  painel_dir (resultados) │
#   │  - Parâmetros de Voo  │  - Gráfico do perfil     │
#   │  - Config da Busca    │  - Top 5 candidatos      │
#   │  - Filtros XFOIL      │  - Resultado final       │
#   │  - [Calcular]         │  - Barra de progresso    │
#   └──────────────────────────────────────────────────┘

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import queue
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Importa o motor principal
import Main as engine
import Enviroment as env
import Optimizer


# ============================================================
# PALETA DE CORES E ESTILOS
# ============================================================

COR = {
    "bg":          "#1A1D23",
    "painel":      "#22262E",
    "card":        "#2A2F3A",
    "borda":       "#3A3F4C",
    "azul":        "#4A9EF5",
    "azul_hover":  "#3A8EE5",
    "verde":       "#4CAF82",
    "amarelo":     "#F5B942",
    "vermelho":    "#E05C5C",
    "texto":       "#E8ECF4",
    "texto_dim":   "#8A92A6",
    "texto_valor": "#FFFFFF",
}

FONTE = {
    "titulo":     ("Consolas", 13, "bold"),
    "label":      ("Consolas", 9),
    "label_bold": ("Consolas", 9, "bold"),
    "entrada":    ("Consolas", 10),
    "resultado":  ("Consolas", 11, "bold"),
    "pequena":    ("Consolas", 8),
    "botao":      ("Consolas", 10, "bold"),
    "mono":       ("Consolas", 9),
}


# ============================================================
# CLASSE PRINCIPAL DA JANELA
# ============================================================

class NacaGUI:

    def __init__(self, root: tk.Tk):
        self.root = root                # Janela principal
        self._configura_janela()        # Faz a configuração inicial da janela
        self._aplica_tema()             # Configura o tema visual dos widgets
        self._cria_layout()             # Cria o layout principal (painel esquerdo e direito)

        self.fila = queue.Queue()       # Queue para comunicação entre a thread de análise e a GUI.
                                        # Threads não podem modificar widgets tkinter diretamente —
                                        # a thread coloca resultados na fila e a GUI lê periodicamente.
        

        self.analisando      = False    # Flag para evitar múltiplas análises simultâneas
        self.resultado_atual = None     # Guarda o resultado atual para exportação


    # ----------------------------------------------------------
    # CONFIGURAÇÃO INICIAL
    # ----------------------------------------------------------

    def _configura_janela(self):
        self.root.title("ZENITH airfoil generator — TCC")       # Título da janela
        self.root.geometry("1200x780")                          # Tamanho inicial da janela quando aberta
        self.root.minsize(1200, 780)                            # Tamanho mínimo da janela para evitar que o layout quebre
        self.root.configure(bg=COR["bg"])                       # Cor de fundo da janela
        self.root.protocol("WM_DELETE_WINDOW", self._ao_fechar) # Garante que a thread de análise seja encerrada ao fechar a janela


    def _aplica_tema(self):
        
        style = ttk.Style()
        style.theme_use("clam")                                         # Usa o tema "clam" como base, que é mais neutro e fácil de customizar

        style.configure("TFrame",        background=COR["bg"])          # Cor de fundo padrão para frames
        style.configure("Card.TFrame",   background=COR["card"])        # Estilo para "cards" com borda
        style.configure("Painel.TFrame", background=COR["painel"])      # Estilo para painéis laterais


        style.configure("TLabel",                                       # Estilo para labels padrão
            background=COR["card"], foreground=COR["texto_dim"],        
            font=FONTE["label"])
        
        
        style.configure("Titulo.TLabel",                                # Estilo para títulos de seções
            background=COR["painel"], foreground=COR["azul"],
            font=FONTE["titulo"])
        
        
        style.configure("Resultado.TLabel",                             # Estilo para labels de resultados finais
            background=COR["card"], foreground=COR["verde"],
            font=FONTE["resultado"])
        
        
        style.configure("Info.TLabel",                                  # Estilo para labels de informações calculadas (Reynolds, Mach, etc)
            background=COR["card"], foreground=COR["texto"],
            font=FONTE["mono"])
        

        style.configure("TEntry",                                       # Estilo para campos de entrada
            fieldbackground=COR["bg"], foreground=COR["texto_valor"],
            insertcolor=COR["azul"], font=FONTE["entrada"],
            borderwidth=1, relief="flat")


        style.configure("Calcular.TButton",                             # Estilo específico para o botão "Calcular"
            background=COR["azul"], foreground="#FFFFFF",
            font=FONTE["botao"], padding=(20, 10), relief="flat")
        
        style.map("Calcular.TButton",                                   # Efeito hover para o botão "Calcular"
            background=[("active", COR["azul_hover"]),
                        ("disabled", COR["borda"])])


        style.configure("TButton",
            background=COR["card"], foreground=COR["texto"],
            font=FONTE["label_bold"], padding=(10, 6), relief="flat")
        
        style.map("TButton",
            background=[("active", COR["borda"])])
        

        style.configure("TSeparator", background=COR["borda"])


        style.configure("TProgressbar",
            background=COR["azul"], troughcolor=COR["card"], thickness=4)


        style.configure("TLabelframe",
            background=COR["card"], foreground=COR["texto_dim"],
            bordercolor=COR["borda"])
        
        
        style.configure("TLabelframe.Label",
            background=COR["card"], foreground=COR["azul"],
            font=FONTE["label_bold"])


    # ----------------------------------------------------------
    # LAYOUT PRINCIPAL
    # ----------------------------------------------------------

    def _cria_layout(self):
        # Título no topo
        frame_topo = tk.Frame(self.root, bg=COR["bg"], pady=12)
        frame_topo.pack(fill="x", padx=20)

        tk.Label(frame_topo,
            text="✈  WINGLABS AIRFOIL",
            bg=COR["bg"], fg=COR["azul"],
            font=("Consolas", 15, "bold")
        ).pack(side="left")

        tk.Label(frame_topo,
            text="Gerador de Asas NACA",
            bg=COR["bg"], fg=COR["texto_dim"],
            font=FONTE["label"]
        ).pack(side="left", padx=(12, 0), pady=(4, 0))

        tk.Frame(self.root, bg=COR["borda"], height=1).pack(fill="x", padx=20)

        container = tk.Frame(self.root, bg=COR["bg"])
        container.pack(fill="both", expand=True, padx=20, pady=12)

        # Painel esquerdo — inputs (largura fixa)
        self.painel_esq = tk.Frame(container, bg=COR["painel"], width=230)
        self.painel_esq.pack(side="left", fill="y", padx=(0, 10))
        self.painel_esq.pack_propagate(False)

        # Painel direito — resultados (expande)
        self.painel_dir = tk.Frame(container, bg=COR["painel"])
        self.painel_dir.pack(side="left", fill="both", expand=True)

        self._cria_inputs()
        self._cria_outputs()


    # ----------------------------------------------------------
    # PAINEL ESQUERDO — INPUTS
    # ----------------------------------------------------------

    def _bind_mousewheel(self, widget):
        widget.bind("<MouseWheel>",
            lambda e: self._on_mousewheel(e))
        for child in widget.winfo_children():
            self._bind_mousewheel(child)
        
    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(-1*(event.delta//120), "units")

    def _cria_inputs(self):
        # Canvas com scrollbar para o painel esquerdo ser rolável
        self.canvas = tk.Canvas(self.painel_esq, bg=COR["painel"],
                           highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.painel_esq, orient="vertical",
                                   command=self.canvas.yview)
        self.frame_scroll = tk.Frame(self.canvas, bg=COR["painel"])

        self.frame_scroll.bind("<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

        self.canvas.create_window((0, 0), window=self.frame_scroll, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        

        scroll_lock = self.frame_scroll

        # Grupos de campos
        self.vars_voo = {}
        self._cria_grupo(scroll_lock, "⬡  Parâmetros de Voo", [
            ("altitude",   "Altitude (m)",         "1500"),
            ("velocity",  "Velocidade (m/s)",     "60"),
            ("target_cl",    "CL alvo",              "0.8"),
            ("chord_m",      "Corda (m)",            "1.2"),
        ], self.vars_voo)
        

        frame_calc = self._frame_card(scroll_lock, "⬡  Atmosfera ISA")
        self.label_reynolds = self._info_label(frame_calc, "Reynolds", "—")
        self.label_mach     = self._info_label(frame_calc, "Mach",     "—")
        self.label_rho      = self._info_label(frame_calc, "ρ (kg/m³)","—")
        ttk.Button(frame_calc, text="Atualizar",
                   command=self._atualiza_dados
        ).pack(fill="x", padx=10, pady=(4, 8))

        self.vars_busca = {}
        self._cria_grupo(scroll_lock, "⬡  Configurações da Busca", [
            ("cl_tolerance", "Tolerância CL (±)",       "0.01"),
            ("camber_max",    "Camber máximo (0-9)",     "6"),
            ("espessuras",    "Espessuras (ex: 8,12,15)","8,10,12,15,18"),
        ], self.vars_busca)

        self.vars_xfoil = {}
        self._cria_grupo(scroll_lock, "⬡  Parâmetros do XFOIL", [
            ("alpha_start", "Alpha início (°)",  "0"),
            ("alpha_end",   "Alpha fim (°)",     "0"),
            ("alpha_step",  "Passo alpha (°)",   "0.5"),
            ("n_panels",    "Nº de painéis",     "240"),
            ("n_threads",     "Threads paralelas",       "1"),
            ("n_iterations",  "Iterações",         "100")
        ], self.vars_xfoil)

        self.vars_filtros = {}
        self._cria_grupo(scroll_lock, "⬡  Filtros Físicos", [
            ("cd_min",  "CD mínimo (0=auto)",  "0"),
            ("eff_max", "CL/CD máx (0=auto)",  "0"),
        ], self.vars_filtros)

        self._bind_mousewheel(self.frame_scroll)

        # Botões
        frame_btns = tk.Frame(scroll_lock, bg=COR["painel"], pady=10)
        frame_btns.pack(fill="x", padx=10)

        self.btn_calcular = ttk.Button(
            frame_btns, text="▶  CALCULAR",
            style="Calcular.TButton",
            command=self._iniciar_analise
        )
        self.btn_calcular.pack(fill="x", pady=(0, 6))

        ttk.Button(frame_btns, text="↺  Resetar padrões",
                   command=self._resetar_padrao
        ).pack(fill="x")

        self.progresso = ttk.Progressbar(scroll_lock, mode="indeterminate")
        self.label_status = tk.Label(scroll_lock, text="", bg=COR["painel"],
                                      fg=COR["texto_dim"], font=FONTE["pequena"])
        self.label_status.pack(pady=(4, 0))


    def _cria_grupo(self, parent, titulo: str, campos: list, dicionario: dict):     # Cria um grupo de campos de entrada (LabelFrame com Entries).
        
        frame = self._frame_card(parent, titulo)
        for key, label_txt, padrao in campos:
            tk.Label(frame, text=label_txt,
                     bg=COR["card"], fg=COR["texto_dim"],
                     font=FONTE["label"]
            ).pack(anchor="w", padx=10, pady=(6, 0))

            var = tk.StringVar(value=padrao)
            if titulo == "⬡  Parâmetros de Voo":
                var.trace_add("write", lambda *args: self._atualiza_dados())
            tk.Entry(frame, textvariable=var,
                     bg=COR["bg"], fg=COR["texto_valor"],
                     insertbackground=COR["azul"],
                     font=FONTE["entrada"], relief="flat", bd=4
            ).pack(fill="x", padx=10, pady=(2, 0))
            dicionario[key] = var

        tk.Frame(frame, bg=COR["card"], height=8).pack()


    def _frame_card(self, parent, titulo: str) -> tk.Frame:                             # Cria um card com borda e título, retorna o frame interno.
        
        outer = tk.Frame(parent, bg=COR["borda"], pady=1)
        outer.pack(fill="x", padx=10, pady=5)
        inner = tk.Frame(outer, bg=COR["card"])
        inner.pack(fill="x", padx=1, pady=1)
        tk.Label(inner, text=titulo,
                 bg=COR["card"], fg=COR["azul"],
                 font=FONTE["label_bold"]
        ).pack(anchor="w", padx=10, pady=(8, 2))
        tk.Frame(inner, bg=COR["borda"], height=1).pack(fill="x", padx=10)
        return inner


    def _info_label(self, parent, nome: str, valor: str) -> tk.Label:
        """Cria linha de info calculada (nome: valor), retorna o label do valor."""
        frame = tk.Frame(parent, bg=COR["card"])
        frame.pack(fill="x", padx=10, pady=2)
        tk.Label(frame, text=f"{nome}:",
                 bg=COR["card"], fg=COR["texto_dim"],
                 font=FONTE["label"], width=12, anchor="w"
        ).pack(side="left")
        lbl = tk.Label(frame, text=valor,
                       bg=COR["card"], fg=COR["azul"],
                       font=FONTE["label_bold"])
        lbl.pack(side="left")
        return lbl


    # ----------------------------------------------------------
    # PAINEL DIREITO — OUTPUTS
    # ----------------------------------------------------------

    def _cria_outputs(self):
        p = self.painel_dir

        # Gráfico matplotlib embutido
        frame_grafico = tk.Frame(p, bg=COR["painel"])
        frame_grafico.pack(fill="both", expand=True, padx=10, pady=(10, 5))

        self.fig, self.ax = plt.subplots(figsize=(7, 2.8),
                                          facecolor=COR["painel"])
        self.ax.set_facecolor(COR["card"])
        self._limpa_grafico()

        # FigureCanvasTkAgg embute o matplotlib dentro do tkinter
        self.canvas_fig = FigureCanvasTkAgg(self.fig, master=frame_grafico)
        self.canvas_fig.draw()
        self.canvas_fig.get_tk_widget().pack(fill="both", expand=True)

        # Resultados
        frame_res = tk.Frame(p, bg=COR["painel"])
        frame_res.pack(fill="x", padx=10, pady=(0, 10))

        # Top 5
        frame_top5 = self._frame_card(frame_res, "⬡  Top candidatos")
        self.texto_top5 = tk.Text(
            frame_top5, bg=COR["bg"], fg=COR["texto"],
            font=FONTE["mono"], height=7, relief="flat", bd=6,
            state="disabled"
        )
        self.texto_top5.pack(fill="x", padx=10, pady=(4, 8))
        self.texto_top5.tag_configure("header",
            foreground=COR["texto_dim"], font=FONTE["pequena"])
        self.texto_top5.tag_configure("melhor",
            foreground=COR["verde"], font=("Consolas", 9, "bold"))
        self.texto_top5.tag_configure("normal", foreground=COR["texto"])

        # Resultado final
        frame_final = tk.Frame(frame_res, bg=COR["painel"])
        frame_final.pack(fill="x", pady=(6, 0))

        frame_labels = self._frame_card(frame_final, "⬡  Melhor perfil")
        grid = tk.Frame(frame_labels, bg=COR["card"])
        grid.pack(fill="x", padx=10, pady=8)

        self.label_naca  = self._resultado_label(grid, "Código NACA",  "—", 0)
        self.label_cl    = self._resultado_label(grid, "CL",           "—", 1)
        self.label_cd    = self._resultado_label(grid, "CD",           "—", 2)
        self.label_clcd  = self._resultado_label(grid, "CL/CD",        "—", 3)
        self.label_alpha = self._resultado_label(grid, "Ângulo ideal", "—", 4)

        # Botões de export
        frame_export = tk.Frame(frame_final, bg=COR["painel"])
        frame_export.pack(fill="x", pady=(8, 0))

        for texto, tipo in [("💾  SVG", "svg"),
                             ("💾  DAT", "dat"),
                             ("💾  JSON", "json")]:
            ttk.Button(frame_export, text=texto,
                       command=lambda t=tipo: self._exportar(t)
            ).pack(side="left", padx=(0, 4))


    def _resultado_label(self, parent, nome: str, valor: str,
                          row: int) -> tk.Label:
        tk.Label(parent, text=f"{nome}:",
                 bg=COR["card"], fg=COR["texto_dim"],
                 font=FONTE["label"], width=14, anchor="w"
        ).grid(row=row, column=0, sticky="w", pady=2)
        lbl = tk.Label(parent, text=valor,
                       bg=COR["card"], fg=COR["verde"],
                       font=FONTE["resultado"])
        lbl.grid(row=row, column=1, sticky="w", padx=(8, 0))
        return lbl


    # ----------------------------------------------------------
    # LÓGICA — LEITURA DE INPUTS
    # ----------------------------------------------------------

    def _le_float(self, dic, key, default):
        try:    return float(dic[key].get())
        except: return default

    def _le_int(self, dic, key, default):
        try:    return int(dic[key].get())
        except: return default

    def _le_espessuras(self):
        try:
            raw = self.vars_busca["espessuras"].get()
            return [int(e.strip()) for e in raw.split(",")]
        except:
            return [8, 10, 12, 15, 18]

    def _monta_cond_cfg(self):
        """Lê todos os campos e monta FlightConditions + cfg."""
        cond = engine.Enviroment.FlightConditions(
            altitude        = self._le_float(self.vars_voo, "altitude",   1500),
            velocity        = self._le_float(self.vars_voo, "velocity",  60),
            target_cl       = self._le_float(self.vars_voo, "target_cl",    0.8),
            chord_size      = self._le_float(self.vars_voo, "chord_m",      1.2),
        )
        cd_min_val  = self._le_float(self.vars_filtros, "cd_min",  0)
        eff_max_val = self._le_float(self.vars_filtros, "eff_max", 0)

        cfg = {
            "cl_tolerance": self._le_float(self.vars_busca,  "cl_tolerance", 0.01),
            "camber_max":    self._le_int(  self.vars_busca,  "camber_max",    6),
            "espessuras":    self._le_espessuras(),
            "cd_min":        cd_min_val if cd_min_val > 0 else env.min_Cd(cond.reynolds),
            "eff_max":       eff_max_val if eff_max_val > 0 else env.max_efficiency(cond.reynolds),
            "alpha_start":   self._le_float(self.vars_xfoil, "alpha_start", 0),
            "alpha_end":     self._le_float(self.vars_xfoil, "alpha_end",   0),
            "alpha_step":    self._le_float(self.vars_xfoil, "alpha_step",  0.5),
            "n_panels":      self._le_int(  self.vars_xfoil, "n_panels",    240),
            "n_threads":     self._le_int(  self.vars_xfoil,  "n_threads",     1),
            "n_iterations":  self._le_int(  self.vars_xfoil,  "n_iterations", 100)
        }
        return cond, cfg


    # ----------------------------------------------------------
    # LÓGICA — ATMOSFERA            TODO: Atualizar os dados imediatamente apos o usuario alterar os dados iniciais
    # ----------------------------------------------------------

    def _atualiza_dados(self):
        try:
            cond, _ = self._monta_cond_cfg()
            self.label_reynolds.config(text=f"{cond.reynolds:,.0f}")
            self.label_mach.config(    text=f"{cond.mach:.4f}")
            self.label_rho.config(     text=f"{cond.rho:.4f}")
        except Exception:
            self.label_reynolds.config(text="erro")

    # ----------------------------------------------------------
    # LÓGICA — ANÁLISE PRINCIPAL
    # ----------------------------------------------------------

    def _iniciar_analise(self):
    
        if self.analisando:
            return

        try:
            cond, cfg = self._monta_cond_cfg()
        except Exception as e:
            messagebox.showerror("Erro nos parâmetros", str(e))
            return

        if not engine.XFOIL_PATH.exists():
            messagebox.showerror("xfoil.exe não encontrado",
                f"Coloque o xfoil.exe em:\n{engine.XFOIL_PATH}")
            return

        self.analisando = True
        self.btn_calcular.config(state="disabled")
        self.progresso.pack(fill="x", padx=10, pady=(4, 0))
        self.progresso.start(10)
        self._set_status("Analisando perfis NACA...")
        self._limpa_resultados()

        # daemon=True: a thread morre junto com a janela
        threading.Thread(
            target=self._thread_analise,
            args=(cond, cfg),
        ).start()

        self.root.after(100, self._checa_fila)


    def _thread_analise(self, cond, cfg):
        try:
            best_code, result, top5 = Optimizer.run(cond, cfg)
            self.fila.put(("ok", best_code, result, top5, cond))
        except Exception as e:
            self.fila.put(("erro", str(e)))


    def _checa_fila(self):
        
        try:
            msg = self.fila.get_nowait()

            self.progresso.stop()
            self.progresso.pack_forget()
            self.analisando = False
            self.btn_calcular.config(state="normal")

            if msg[0] == "erro":
                self._set_status(f"Erro: {msg[1]}", COR["vermelho"])
                messagebox.showerror("Erro na análise", msg[1])
            else:
                _, best_code, result, top5, cond = msg
                if result is None:
                    self._set_status("Nenhum perfil passou nos filtros.",
                                     COR["amarelo"])
                else:
                    self._exibe_resultado(best_code, result, top5, cond)
                    self._set_status(
                        f"Concluído! Melhor: NACA {best_code}", COR["verde"])

        except queue.Empty:
            # Ainda processando — agenda próxima verificação em 100ms
            self.root.after(100, self._checa_fila)


    # ----------------------------------------------------------
    # EXIBIÇÃO DOS RESULTADOS
    # ----------------------------------------------------------

    def _exibe_resultado(self, best_code, result, top5, cond):
        self.resultado_atual = {
            "code": best_code, "result": result,
            "top5": top5, "cond": cond
        }
        self.label_naca.config( text=f"NACA {best_code}")
        self.label_cl.config(   text=f"{result['cl']:.4f}")
        self.label_cd.config(   text=f"{result['cd']:.5f}")
        self.label_clcd.config( text=f"{result['efficiency']:.2f}")
        self.label_alpha.config(text=f"{result['alpha_opt']:.1f}°")

        self._atualiza_top5(top5)

        x, y = engine.nacaGenerator(best_code, n_points=500)
        self._desenha_perfil(x, y, best_code, result)


    def _atualiza_top5(self, top5: list):
        self.texto_top5.config(state="normal")
        self.texto_top5.delete("1.0", "end")

        header = f"  {'#':<3} {'NACA':<8} {'CL':>7} {'CD':>8} {'CL/CD':>7} {'α':>6}\n"
        header += f"  {'─'*44}\n"
        self.texto_top5.insert("end", header, "header")

        for i, (code, res) in enumerate(top5):
            linha = (f"  {i+1:<3} {code:<8} "
                     f"{res['cl']:>7.4f} {res['cd']:>8.5f} "
                     f"{res['efficiency']:>7.2f} {res['alpha_opt']:>5.1f}°\n")
            tag = "melhor" if i == 0 else "normal"
            self.texto_top5.insert("end", linha, tag)

        self.texto_top5.config(state="disabled")


    def _desenha_perfil(self, x, y, code, result):
        self.ax.clear()
        self.ax.set_facecolor(COR["card"])
        self.ax.plot(x, y, color=COR["azul"], linewidth=1.8,
                     label=f"NACA {code}")
        self.ax.fill(x, y, alpha=0.15, color=COR["azul"])
        self.ax.set_aspect("equal")
        self.ax.grid(True, alpha=0.15, color=COR["borda"])
        self.ax.set_xlabel("x/c", color=COR["texto_dim"], fontsize=8)
        self.ax.set_ylabel("y/c", color=COR["texto_dim"], fontsize=8)
        self.ax.tick_params(colors=COR["texto_dim"], labelsize=7)
        for spine in self.ax.spines.values():
            spine.set_edgecolor(COR["borda"])
        self.ax.set_title(
            f"NACA {code}   |   CL={result['cl']:.3f}   "
            f"CD={result['cd']:.4f}   CL/CD={result['efficiency']:.1f}   "
            f"α={result['alpha_opt']:.1f}°",
            color=COR["texto"], fontsize=9, pad=8
        )
        self.ax.legend(loc="upper right", fontsize=8,
                       facecolor=COR["card"], edgecolor=COR["borda"],
                       labelcolor=COR["texto"])
        self.canvas_fig.draw()


    def _limpa_grafico(self):
        self.ax.clear()
        self.ax.set_facecolor(COR["card"])
        self.ax.text(0.5, 0.5, "O perfil aparecerá aqui após a análise",
                     transform=self.ax.transAxes, ha="center", va="center",
                     color=COR["texto_dim"], fontsize=9, style="italic")
        self.ax.set_xticks([])
        self.ax.set_yticks([])
        for spine in self.ax.spines.values():
            spine.set_edgecolor(COR["borda"])


    def _limpa_resultados(self):
        for lbl in [self.label_naca, self.label_cl, self.label_cd,
                    self.label_clcd, self.label_alpha]:
            lbl.config(text="—")
        self.texto_top5.config(state="normal")
        self.texto_top5.delete("1.0", "end")
        self.texto_top5.config(state="disabled")
        self._limpa_grafico()
        self.canvas_fig.draw()
        self.resultado_atual = None


    # ----------------------------------------------------------
    # EXPORTAÇÃO
    # ----------------------------------------------------------

    def _exportar(self, tipo: str):
        if self.resultado_atual is None:
            messagebox.showwarning("Sem resultado",
                                   "Rode a análise antes de exportar.")
            return

        code   = self.resultado_atual["code"]
        result = self.resultado_atual["result"]
        cond   = self.resultado_atual["cond"]
        x, y   = engine.nacaGenerator(code, n_points=300)

        extensoes    = {"svg": [("SVG","*.svg")],
                        "dat": [("DAT","*.dat")],
                        "json":[("JSON","*.json")]}
        nome_padrao  = {"svg": f"naca_{code}.svg",
                        "dat": f"naca_{code}.dat",
                        "json":f"naca_{code}_result.json"}

        caminho = filedialog.asksaveasfilename(
            defaultextension=f".{tipo}",
            filetypes=extensoes[tipo],
            initialfile=nome_padrao[tipo]
        )
        if not caminho:
            return

        out = Path(caminho).parent
        try:
            if tipo == "svg":
                engine.export_svg(x, y, code, out)
            elif tipo == "dat":
                engine.export_dat(x, y, code, out)
            elif tipo == "json":
                engine.export_json(code, result, cond, Path(f"naca_{code}.dat"), out)
            messagebox.showinfo("Exportado!", f"Arquivo salvo em:\n{caminho}")
        except Exception as e:
            messagebox.showerror("Erro ao exportar", str(e))


    # ----------------------------------------------------------
    # UTILITÁRIOS
    # ----------------------------------------------------------

    def _set_status(self, msg: str, cor: str = ""):
        self.label_status.config(text=msg,
                                  fg=cor if cor else COR["texto_dim"])

    def _resetar_padrao(self):
        defaults = [
            (self.vars_voo, {
                "altitude":"1500","velocity":"60","target_cl":"0.8",
                "chord_m":"1.2"}),
            (self.vars_busca, {
                "cl_tolerance":"0.15",
                "camber_max":"6","espessuras":"8,10,12,15,18"}),
            (self.vars_xfoil, {
                "alpha_start":"0","alpha_end":"0",
                "alpha_step":"0.5","n_panels":"240","n_threads":"1","n_iterations":"100"}),
            (self.vars_filtros, {"cd_min":"0","eff_max":"0"}),
        ]
        for dic, vals in defaults:
            for i, v in vals.items():
                dic[i].set(v)
        self._atualiza_dados()
        # self._limpa_resultados()
        self._set_status("Padrões restaurados.")

    def _ao_fechar(self):
        if self.analisando:
            if not messagebox.askyesno(
                "Análise em andamento",
                "Uma análise está em andamento. Deseja fechar mesmo assim?"
            ):
                return
        plt.close("all")
        self.root.destroy()


# ============================================================
# PONTO DE ENTRADA
# ============================================================

def main():
    root = tk.Tk()
    app  = NacaGUI(root)
    app._atualiza_dados()
    root.mainloop()


if __name__ == "__main__":
    main()
