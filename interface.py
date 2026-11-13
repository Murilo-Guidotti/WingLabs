# ============================================================
# WingLabs Studio — Interface Gráfica Unificada (Módulo 1 + 2)
# TCC — Gerador e Otimizador de Asas NACA 2D/3D
# ============================================================

from __future__ import annotations

import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401

import Enviroment as env
import main as engine
import optimizer
import pipeline


# ============================================================
# PALETA DE CORES & TIPOGRAFIA (DARK AEROSPACE CAD)
# ============================================================

COR = {
    "bg":           "#0D1117",
    "sidebar":      "#131922",
    "surface":      "#18202C",
    "card":         "#1E2836",
    "card_hover":   "#243142",
    "card_active":  "#172C40",
    "borda":        "#2A3648",
    "azul":         "#38BDF8",
    "azul_hover":   "#0EA5E9",
    "azul_dim":     "#1D4E6B",
    "verde":        "#34D399",
    "amarelo":      "#FBBF24",
    "vermelho":     "#F87171",
    "texto":        "#F1F5F9",
    "texto_sec":    "#94A3B8",
    "texto_dim":    "#64748B",
}

FONTE = {
    "brand":      ("Segoe UI", 14, "bold"),
    "sub":        ("Segoe UI", 9),
    "sec":        ("Segoe UI", 9, "bold"),
    "label":      ("Segoe UI", 9),
    "entrada":    ("Consolas", 10),
    "valor":      ("Consolas", 10, "bold"),
    "kpi":        ("Consolas", 12, "bold"),
    "botao":      ("Segoe UI", 10, "bold"),
    "pequena":    ("Segoe UI", 8),
    "mono":       ("Consolas", 9),
}


class WingLabsGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.fila: queue.Queue = queue.Queue()
        self.analisando = False
        self.gerando_3d = False

        self.top4: list[tuple[str, dict]] = []
        self.cond_atual: env.FlightConditions | None = None
        self.cfg_atual: dict | None = None
        self.selected_idx: int = 0
        self.search_mode = tk.StringVar(value="payload")
        self.auto_pipeline = tk.BooleanVar(value=True)

        self._configura_janela()
        self._aplica_tema()
        self._cria_layout()
        self._atualiza_modo_ui()
        self._atualiza_dados()
        self._desenha_3d_preview("2412")

    # ----------------------------------------------------------
    # CONFIGURAÇÃO DA JANELA & TEMA
    # ----------------------------------------------------------

    def _configura_janela(self):
        self.root.title("WingLabs Studio — Otimizador 2D & Gerador 3D de Asas")
        self.root.geometry("1400x860")
        self.root.minsize(1240, 780)
        self.root.configure(bg=COR["bg"])
        self.root.protocol("WM_DELETE_WINDOW", self._ao_fechar)

    def _aplica_tema(self):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure("TFrame", background=COR["bg"])
        style.configure("TLabel", background=COR["card"], foreground=COR["texto_sec"], font=FONTE["label"])
        style.configure(
            "Primary.TButton",
            background=COR["azul"],
            foreground="#081018",
            font=FONTE["botao"],
            padding=(14, 10),
            borderwidth=0,
        )
        style.map(
            "Primary.TButton",
            background=[("active", COR["azul_hover"]), ("disabled", COR["borda"])],
            foreground=[("disabled", COR["texto_dim"])],
        )
        style.configure(
            "Accent.TButton",
            background=COR["verde"],
            foreground="#062016",
            font=FONTE["botao"],
            padding=(12, 8),
            borderwidth=0,
        )
        style.map(
            "Accent.TButton",
            background=[("active", "#10B981"), ("disabled", COR["borda"])],
            foreground=[("disabled", COR["texto_dim"])],
        )
        style.configure(
            "Ghost.TButton",
            background=COR["card"],
            foreground=COR["texto"],
            font=FONTE["sec"],
            padding=(10, 7),
            borderwidth=1,
        )
        style.map("Ghost.TButton", background=[("active", COR["card_hover"])])

        style.configure(
            "Wing.Horizontal.TProgressbar",
            background=COR["azul"],
            troughcolor=COR["surface"],
            borderwidth=0,
            thickness=6,
        )

    # ----------------------------------------------------------
    # LAYOUT PRINCIPAL
    # ----------------------------------------------------------

    def _cria_layout(self):
        # Header superior
        header = tk.Frame(self.root, bg=COR["sidebar"], height=56)
        header.pack(fill="x")
        header.pack_propagate(False)

        left_h = tk.Frame(header, bg=COR["sidebar"])
        left_h.pack(side="left", padx=20)
        tk.Label(
            left_h, text="✈  WINGLABS STUDIO",
            bg=COR["sidebar"], fg=COR["azul"], font=FONTE["brand"]
        ).pack(side="left")
        tk.Label(
            left_h, text="  |  Pipeline Autônoma XFOIL 2D → PicoGK 3D",
            bg=COR["sidebar"], fg=COR["texto_sec"], font=FONTE["sub"]
        ).pack(side="left", pady=(2, 0))

        self.badge_pipeline = tk.Label(
            header, text="● PRONTO", bg=COR["card"], fg=COR["verde"],
            font=FONTE["pequena"], padx=10, pady=4
        )
        self.badge_pipeline.pack(side="right", padx=20)

        tk.Frame(self.root, bg=COR["borda"], height=1).pack(fill="x")

        # Corpo principal: Sidebar esquerda + Área de trabalho direita
        body = tk.Frame(self.root, bg=COR["bg"])
        body.pack(fill="both", expand=True, padx=14, pady=12)

        self.sidebar = tk.Frame(body, bg=COR["sidebar"], width=340)
        self.sidebar.pack(side="left", fill="y", padx=(0, 12))
        self.sidebar.pack_propagate(False)

        self.workspace = tk.Frame(body, bg=COR["bg"])
        self.workspace.pack(side="left", fill="both", expand=True)

        self._cria_sidebar()
        self._cria_workspace()

    # ----------------------------------------------------------
    # SIDEBAR ESQUERDA (INPUTS & PIPELINE)
    # ----------------------------------------------------------

    def _cria_sidebar(self):
        self.canvas_sb = tk.Canvas(self.sidebar, bg=COR["sidebar"], highlightthickness=0)
        sb = ttk.Scrollbar(self.sidebar, orient="vertical", command=self.canvas_sb.yview)
        self.frame_sb = tk.Frame(self.canvas_sb, bg=COR["sidebar"])

        self.frame_sb.bind(
            "<Configure>",
            lambda e: self.canvas_sb.configure(scrollregion=self.canvas_sb.bbox("all")),
        )
        win_id = self.canvas_sb.create_window((0, 0), window=self.frame_sb, anchor="nw")
        self.canvas_sb.bind(
            "<Configure>",
            lambda e: self.canvas_sb.itemconfigure(win_id, width=e.width),
        )
        self.canvas_sb.configure(yscrollcommand=sb.set)
        self.canvas_sb.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        p = self.frame_sb

        # Seletor de Modo de Busca
        card_modo = self._card(p, "MODO DE OTIMIZAÇÃO (MÓDULO 1)")
        seg = tk.Frame(card_modo, bg=COR["card"])
        seg.pack(fill="x", padx=10, pady=(6, 8))

        self.btn_modo_payload = tk.Button(
            seg, text="Carga / Peso (kg)", relief="flat", cursor="hand2",
            font=FONTE["sec"], pady=6,
            command=lambda: self._set_modo("payload"),
        )
        self.btn_modo_payload.pack(side="left", fill="x", expand=True, padx=(0, 3))

        self.btn_modo_cl = tk.Button(
            seg, text="CL Alvo Fixo", relief="flat", cursor="hand2",
            font=FONTE["sec"], pady=6,
            command=lambda: self._set_modo("target_cl"),
        )
        self.btn_modo_cl.pack(side="left", fill="x", expand=True, padx=(3, 0))

        # Cenário de Voo
        self.vars_voo: dict[str, tk.StringVar] = {}
        card_voo = self._card(p, "CENÁRIO DE VOO")
        self._campo(card_voo, "altitude", "Altitude (m)", "1500", self.vars_voo, self._atualiza_dados)
        self._campo(card_voo, "velocity", "Velocidade (m/s)", "60", self.vars_voo, self._atualiza_dados)

        self.frame_payload_input = tk.Frame(card_voo, bg=COR["card"])
        self._campo(self.frame_payload_input, "payload_kg", "Peso da Carga / Massa (kg)", "120", self.vars_voo, self._atualiza_dados)

        self.frame_cl_input = tk.Frame(card_voo, bg=COR["card"])
        self._campo(self.frame_cl_input, "target_cl", "CL Alvo", "0.8", self.vars_voo, self._atualiza_dados)

        # Resumo Atmosférico + CL Requerido ao vivo
        atm_box = tk.Frame(card_voo, bg=COR["surface"], padx=8, pady=6)
        atm_box.pack(fill="x", padx=10, pady=(6, 8))
        self.lbl_re   = self._mini_kv(atm_box, "Reynolds", "—")
        self.lbl_mach = self._mini_kv(atm_box, "Mach", "—")
        self.lbl_rho  = self._mini_kv(atm_box, "ρ Ar (kg/m³)", "—")
        self.lbl_area = self._mini_kv(atm_box, "Área Alar S", "—")
        self.lbl_clreq = self._mini_kv(atm_box, "CL Mín. Carga", "—", COR["verde"])

        # Geometria 3D da Asa (Tempo real + Módulo 2)
        self.vars_3d: dict[str, tk.StringVar] = {}
        card_3d = self._card(p, "GEOMETRIA 3D DA ASA (MÓDULO 2)")
        grid3d = tk.Frame(card_3d, bg=COR["card"])
        grid3d.pack(fill="x", padx=10, pady=(4, 8))
        grid3d.columnconfigure(0, weight=1)
        grid3d.columnconfigure(1, weight=1)

        campos_3d = [
            ("span_mm", "Envergadura (mm)", "5000", 0, 0),
            ("root_chord_mm", "Corda Raiz (mm)", "1200", 0, 1),
            ("tip_chord_mm", "Corda Ponta (mm)", "700", 1, 0),
            ("wing_sweep_deg", "Enflechamento (°)", "15", 1, 1),
            ("tip_twist_deg", "Torção Ponta (°)", "-3", 2, 0),
            ("wing_dihedral_deg", "Diedro (°)", "2", 2, 1),
            ("section_size_mm", "Tam. Seção (mm)", "250", 3, 0),
            ("voxel_size_mm", "Voxel (mm)", "2.5", 3, 1),
        ]
        for key, label, default, r, c in campos_3d:
            cell = tk.Frame(grid3d, bg=COR["card"])
            cell.grid(row=r, column=c, sticky="ew", padx=3, pady=3)
            tk.Label(cell, text=label, bg=COR["card"], fg=COR["texto_sec"], font=FONTE["pequena"]).pack(anchor="w")
            var = tk.StringVar(value=default)
            var.trace_add("write", lambda *_: self._ao_editar_3d())
            tk.Entry(
                cell, textvariable=var, bg=COR["bg"], fg=COR["texto"],
                insertbackground=COR["azul"], font=FONTE["entrada"], relief="flat", bd=4
            ).pack(fill="x", pady=(2, 0))
            self.vars_3d[key] = var

        # Busca & XFOIL
        self.vars_busca: dict[str, tk.StringVar] = {}
        card_busca = self._card(p, "BUSCA & XFOIL")
        g_b = tk.Frame(card_busca, bg=COR["card"])
        g_b.pack(fill="x", padx=10, pady=(4, 8))
        g_b.columnconfigure(0, weight=1)
        g_b.columnconfigure(1, weight=1)

        campos_busca = [
            ("cl_tolerance", "Tolerância CL (±)", "0.15", 0, 0),
            ("camber_max", "Camber Máx (0-9)", "6", 0, 1),
            ("alpha_start", "Alpha Início (°)", "-2", 1, 0),
            ("alpha_end", "Alpha Fim (°)", "12", 1, 1),
            ("alpha_step", "Passo Alpha (°)", "0.5", 2, 0),
            ("n_panels", "Painéis XFOIL", "240", 2, 1),
            ("n_iterations", "Iterações", "100", 3, 0),
            ("n_threads", "Threads", "4", 3, 1),
        ]
        for key, label, default, r, c in campos_busca:
            cell = tk.Frame(g_b, bg=COR["card"])
            cell.grid(row=r, column=c, sticky="ew", padx=3, pady=3)
            tk.Label(cell, text=label, bg=COR["card"], fg=COR["texto_sec"], font=FONTE["pequena"]).pack(anchor="w")
            var = tk.StringVar(value=default)
            tk.Entry(
                cell, textvariable=var, bg=COR["bg"], fg=COR["texto"],
                insertbackground=COR["azul"], font=FONTE["entrada"], relief="flat", bd=4
            ).pack(fill="x", pady=(2, 0))
            self.vars_busca[key] = var

        self._campo(card_busca, "espessuras", "Espessuras (%)", "8,10,12,15,18", self.vars_busca)

        self.vars_filtros: dict[str, tk.StringVar] = {}
        g_f = tk.Frame(card_busca, bg=COR["card"])
        g_f.pack(fill="x", padx=10, pady=(2, 8))
        g_f.columnconfigure(0, weight=1)
        g_f.columnconfigure(1, weight=1)
        for idx_f, (key, label, default) in enumerate([("cd_min", "CD mín (0=auto)", "0"), ("eff_max", "CL/CD máx (0=auto)", "0")]):
            cell = tk.Frame(g_f, bg=COR["card"])
            cell.grid(row=0, column=idx_f, sticky="ew", padx=3)
            tk.Label(cell, text=label, bg=COR["card"], fg=COR["texto_sec"], font=FONTE["pequena"]).pack(anchor="w")
            var = tk.StringVar(value=default)
            tk.Entry(
                cell, textvariable=var, bg=COR["bg"], fg=COR["texto"],
                insertbackground=COR["azul"], font=FONTE["entrada"], relief="flat", bd=4
            ).pack(fill="x", pady=(2, 0))
            self.vars_filtros[key] = var

        # Pipeline Toggle + CTA
        act_box = tk.Frame(p, bg=COR["sidebar"], padx=10, pady=8)
        act_box.pack(fill="x")

        tk.Checkbutton(
            act_box,
            text="Pipeline autônoma: gerar STL 3D ao concluir",
            variable=self.auto_pipeline,
            bg=COR["sidebar"], fg=COR["texto_sec"],
            selectcolor=COR["card"], activebackground=COR["sidebar"],
            activeforeground=COR["texto"], font=FONTE["pequena"],
        ).pack(anchor="w", pady=(0, 8))

        self.btn_calcular = ttk.Button(
            act_box, text="▶  EXECUTAR OTIMIZAÇÃO",
            style="Primary.TButton", command=self._iniciar_analise
        )
        self.btn_calcular.pack(fill="x", pady=(0, 6))

        ttk.Button(
            act_box, text="↺  Restaurar padrões",
            style="Ghost.TButton", command=self._resetar_padrao
        ).pack(fill="x")

        self.progresso = ttk.Progressbar(
            act_box, style="Wing.Horizontal.TProgressbar", mode="determinate", maximum=100
        )
        self.progresso.pack(fill="x", pady=(8, 2))
        self.lbl_status = tk.Label(
            act_box, text="Pronto para iniciar.", bg=COR["sidebar"],
            fg=COR["texto_dim"], font=FONTE["pequena"], anchor="w"
        )
        self.lbl_status.pack(fill="x")

        self._bind_mousewheel(self.frame_sb)

    # ----------------------------------------------------------
    # WORKSPACE DIREITA (TOP 4 CARDS + 2D/3D TEMPO REAL + EXPORTS)
    # ----------------------------------------------------------

    def _cria_workspace(self):
        w = self.workspace

        # 1) Barra Top 4 Asas Selecionáveis
        top_hdr = tk.Frame(w, bg=COR["bg"])
        top_hdr.pack(fill="x", pady=(0, 6))
        tk.Label(
            top_hdr, text="TOP 4 MELHORES ASAS — Clique em qualquer card para visualizar em tempo real e exportar",
            bg=COR["bg"], fg=COR["texto_sec"], font=FONTE["sec"]
        ).pack(side="left")

        self.cards_frame = tk.Frame(w, bg=COR["bg"])
        self.cards_frame.pack(fill="x", pady=(0, 10))
        self.top4_widgets: list[dict] = []

        for i in range(4):
            self.cards_frame.columnconfigure(i, weight=1)
            card = tk.Frame(
                self.cards_frame, bg=COR["card"], highlightbackground=COR["borda"],
                highlightthickness=1, padx=12, pady=10, cursor="hand2"
            )
            card.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 6, 0))

            hdr_row = tk.Frame(card, bg=COR["card"])
            hdr_row.pack(fill="x")
            lbl_rank = tk.Label(hdr_row, text=f"#{i+1}", bg=COR["card"], fg=COR["azul"], font=FONTE["sec"])
            lbl_rank.pack(side="left")
            lbl_tag = tk.Label(hdr_row, text="", bg=COR["card"], fg=COR["verde"], font=FONTE["pequena"])
            lbl_tag.pack(side="right")

            lbl_code = tk.Label(card, text="NACA —", bg=COR["card"], fg=COR["texto"], font=("Consolas", 13, "bold"))
            lbl_code.pack(anchor="w", pady=(2, 4))

            lbl_eff = tk.Label(card, text="CL/CD: —", bg=COR["card"], fg=COR["verde"], font=FONTE["valor"])
            lbl_eff.pack(anchor="w")

            lbl_meta = tk.Label(card, text="CL — | CD — | α —", bg=COR["card"], fg=COR["texto_sec"], font=FONTE["pequena"])
            lbl_meta.pack(anchor="w", pady=(2, 0))

            for widget in (card, hdr_row, lbl_rank, lbl_tag, lbl_code, lbl_eff, lbl_meta):
                widget.bind("<Button-1>", lambda e, idx=i: self._selecionar_asa(idx))

            self.top4_widgets.append({
                "card": card, "hdr": hdr_row, "rank": lbl_rank,
                "tag": lbl_tag, "code": lbl_code, "eff": lbl_eff, "meta": lbl_meta
            })

        # 2) Viewport Split: 2D Airfoil (Esquerda) + 3D Wing Real-Time (Direita)
        view_frame = tk.Frame(w, bg=COR["bg"])
        view_frame.pack(fill="both", expand=True, pady=(0, 10))
        view_frame.columnconfigure(0, weight=1)
        view_frame.columnconfigure(1, weight=1)
        view_frame.rowconfigure(0, weight=1)

        # Painel 2D
        p2d = tk.Frame(view_frame, bg=COR["surface"], highlightbackground=COR["borda"], highlightthickness=1)
        p2d.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        tk.Label(p2d, text="  PERFIL 2D (XFOIL)", bg=COR["surface"], fg=COR["azul"], font=FONTE["sec"], pady=6).pack(anchor="w")

        self.fig_2d, self.ax_2d = plt.subplots(figsize=(5.5, 3.6), facecolor=COR["surface"])
        self.canvas_2d = FigureCanvasTkAgg(self.fig_2d, master=p2d)
        self.canvas_2d.get_tk_widget().pack(fill="both", expand=True, padx=6, pady=(0, 6))
        self._limpa_grafico_2d()

        # Painel 3D
        p3d = tk.Frame(view_frame, bg=COR["surface"], highlightbackground=COR["borda"], highlightthickness=1)
        p3d.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        tk.Label(p3d, text="  ASA 3D EM TEMPO REAL (Arraste para girar)", bg=COR["surface"], fg=COR["azul"], font=FONTE["sec"], pady=6).pack(anchor="w")

        self.fig_3d = plt.figure(figsize=(5.5, 3.6), facecolor=COR["surface"])
        self.ax_3d = self.fig_3d.add_subplot(111, projection="3d")
        self.canvas_3d = FigureCanvasTkAgg(self.fig_3d, master=p3d)
        self.canvas_3d.get_tk_widget().pack(fill="both", expand=True, padx=6, pady=(0, 6))

        # 3) Barra Inferior: KPIs da Asa Selecionada + Botões de Exportação & Pipeline 3D
        bottom = tk.Frame(w, bg=COR["surface"], highlightbackground=COR["borda"], highlightthickness=1, padx=14, pady=10)
        bottom.pack(fill="x")

        kpi_bar = tk.Frame(bottom, bg=COR["surface"])
        kpi_bar.pack(fill="x", pady=(0, 8))
        self.kpi_labels: dict[str, tk.Label] = {}
        for title, key in [
            ("Asa Selecionada", "code"),
            ("CL", "cl"),
            ("CD", "cd"),
            ("Eficiência CL/CD", "eff"),
            ("Ângulo α", "alpha"),
            ("Sustentação", "lift"),
        ]:
            box = tk.Frame(kpi_bar, bg=COR["card"], padx=10, pady=6)
            box.pack(side="left", fill="x", expand=True, padx=(0, 6))
            tk.Label(box, text=title, bg=COR["card"], fg=COR["texto_dim"], font=FONTE["pequena"]).pack(anchor="w")
            lbl = tk.Label(box, text="—", bg=COR["card"], fg=COR["texto"], font=FONTE["kpi"])
            lbl.pack(anchor="w")
            self.kpi_labels[key] = lbl

        btn_bar = tk.Frame(bottom, bg=COR["surface"])
        btn_bar.pack(fill="x")

        for txt, tipo in [("Exportar SVG", "svg"), ("Exportar DAT", "dat"), ("Exportar JSON", "json"), ("Exportar Pacote 2D", "all")]:
            ttk.Button(btn_bar, text=txt, style="Ghost.TButton", command=lambda t=tipo: self._exportar(t)).pack(side="left", padx=(0, 6))

        self.btn_3d = ttk.Button(
            btn_bar, text="⚙  Gerar Asa 3D (.STL via PicoGK)",
            style="Accent.TButton", command=self._gerar_3d_selecionada
        )
        self.btn_3d.pack(side="right")

        # Console compacto da Pipeline
        self.lbl_log = tk.Label(
            bottom, text="Pipeline: selecione uma asa ou execute a otimização.",
            bg=COR["surface"], fg=COR["texto_sec"], font=FONTE["mono"], anchor="w"
        )
        self.lbl_log.pack(fill="x", pady=(8, 0))

    # ----------------------------------------------------------
    # HELPERS DE UI
    # ----------------------------------------------------------

    def _card(self, parent, titulo: str) -> tk.Frame:
        outer = tk.Frame(parent, bg=COR["borda"])
        outer.pack(fill="x", padx=10, pady=5)
        inner = tk.Frame(outer, bg=COR["card"])
        inner.pack(fill="x", padx=1, pady=1)
        tk.Label(
            inner, text=titulo, bg=COR["card"], fg=COR["azul"],
            font=FONTE["pequena"], padx=10, pady=6
        ).pack(anchor="w")
        tk.Frame(inner, bg=COR["borda"], height=1).pack(fill="x", padx=10)
        return inner

    def _campo(self, parent, key: str, label: str, padrao: str, dic: dict, on_change=None):
        tk.Label(parent, text=label, bg=COR["card"], fg=COR["texto_sec"], font=FONTE["pequena"]).pack(anchor="w", padx=10, pady=(6, 0))
        var = tk.StringVar(value=padrao)
        if on_change:
            var.trace_add("write", lambda *_: on_change())
        tk.Entry(
            parent, textvariable=var, bg=COR["bg"], fg=COR["texto"],
            insertbackground=COR["azul"], font=FONTE["entrada"], relief="flat", bd=4
        ).pack(fill="x", padx=10, pady=(2, 4))
        dic[key] = var

    def _mini_kv(self, parent, k: str, v: str, color: str = COR["azul"]) -> tk.Label:
        row = tk.Frame(parent, bg=COR["surface"])
        row.pack(fill="x", pady=1)
        tk.Label(row, text=f"{k}:", bg=COR["surface"], fg=COR["texto_sec"], font=FONTE["pequena"]).pack(side="left")
        lbl = tk.Label(row, text=v, bg=COR["surface"], fg=color, font=FONTE["mono"])
        lbl.pack(side="right")
        return lbl

    def _bind_mousewheel(self, widget):
        widget.bind("<MouseWheel>", lambda e: self.canvas_sb.yview_scroll(-1 * (e.delta // 120), "units"))
        for child in widget.winfo_children():
            self._bind_mousewheel(child)

    def _set_modo(self, modo: str):
        self.search_mode.set(modo)
        self._atualiza_modo_ui()
        self._atualiza_dados()

    def _atualiza_modo_ui(self):
        modo = self.search_mode.get()
        if modo == "payload":
            self.btn_modo_payload.config(bg=COR["azul"], fg="#081018")
            self.btn_modo_cl.config(bg=COR["surface"], fg=COR["texto_sec"])
            self.frame_cl_input.pack_forget()
            self.frame_payload_input.pack(fill="x")
        else:
            self.btn_modo_cl.config(bg=COR["azul"], fg="#081018")
            self.btn_modo_payload.config(bg=COR["surface"], fg=COR["texto_sec"])
            self.frame_payload_input.pack_forget()
            self.frame_cl_input.pack(fill="x")

    # ----------------------------------------------------------
    # LEITURA DE PARÂMETROS & CÁLCULOS AO VIVO
    # ----------------------------------------------------------

    def _f(self, dic, key, default) -> float:
        try:
            return float(dic[key].get())
        except Exception:
            return default

    def _i(self, dic, key, default) -> int:
        try:
            return int(dic[key].get())
        except Exception:
            return default

    def _le_wing_3d(self) -> pipeline.Wing3DParams:
        return pipeline.Wing3DParams(
            span_mm=max(100.0, self._f(self.vars_3d, "span_mm", 5000.0)),
            root_chord_mm=max(50.0, self._f(self.vars_3d, "root_chord_mm", 1200.0)),
            tip_chord_mm=max(20.0, self._f(self.vars_3d, "tip_chord_mm", 700.0)),
            tip_twist_deg=self._f(self.vars_3d, "tip_twist_deg", -3.0),
            wing_sweep_deg=self._f(self.vars_3d, "wing_sweep_deg", 15.0),
            wing_dihedral_deg=self._f(self.vars_3d, "wing_dihedral_deg", 2.0),
            target_section_size_mm=max(20.0, self._f(self.vars_3d, "section_size_mm", 250.0)),
            voxel_size_mm=max(0.5, self._f(self.vars_3d, "voxel_size_mm", 2.5)),
        )

    def _monta_cond_cfg(self):
        w3d = self._le_wing_3d()
        chord_m = w3d.root_chord_mm / 1000.0
        altitude = self._f(self.vars_voo, "altitude", 1500.0)
        velocity = max(1.0, self._f(self.vars_voo, "velocity", 60.0))
        area_m2 = env.wing_area_m2(w3d.span_mm, w3d.root_chord_mm, w3d.tip_chord_mm)
        modo = self.search_mode.get()

        payload_kg = self._f(self.vars_voo, "payload_kg", 120.0)
        cond_tmp = env.FlightConditions(altitude=altitude, velocity=velocity, target_cl=0.8, chord_size=chord_m)

        if modo == "payload":
            req_cl = env.required_cl(payload_kg, cond_tmp.rho, velocity, area_m2)
            target_cl = req_cl
        else:
            target_cl = self._f(self.vars_voo, "target_cl", 0.8)
            req_cl = target_cl

        cond = env.FlightConditions(
            altitude=altitude,
            velocity=velocity,
            target_cl=target_cl,
            chord_size=chord_m,
        )

        try:
            espessuras = [int(e.strip()) for e in self.vars_busca["espessuras"].get().split(",") if e.strip()]
            if not espessuras:
                espessuras = [8, 10, 12, 15, 18]
        except Exception:
            espessuras = [8, 10, 12, 15, 18]

        cd_min_val = self._f(self.vars_filtros, "cd_min", 0.0)
        eff_max_val = self._f(self.vars_filtros, "eff_max", 0.0)

        cfg = {
            "search_mode":  modo,
            "payload_kg":   payload_kg if modo == "payload" else None,
            "required_cl":  req_cl,
            "wing_area_m2": area_m2,
            "cl_tolerance": self._f(self.vars_busca, "cl_tolerance", 0.15),
            "camber_max":   self._i(self.vars_busca, "camber_max", 6),
            "espessuras":   espessuras,
            "cd_min":       cd_min_val if cd_min_val > 0 else env.min_Cd(cond.reynolds),
            "eff_max":      eff_max_val if eff_max_val > 0 else env.max_efficiency(cond.reynolds),
            "alpha_start":  self._f(self.vars_busca, "alpha_start", -2.0),
            "alpha_end":    self._f(self.vars_busca, "alpha_end", 12.0),
            "alpha_step":   self._f(self.vars_busca, "alpha_step", 0.5),
            "n_panels":     self._i(self.vars_busca, "n_panels", 240),
            "n_threads":    self._i(self.vars_busca, "n_threads", 4),
            "n_ITER":       self._i(self.vars_busca, "n_iterations", 100),
        }
        return cond, cfg, w3d

    def _atualiza_dados(self):
        try:
            cond, cfg, _ = self._monta_cond_cfg()
            self.lbl_re.config(text=f"{cond.reynolds:,.0f}")
            self.lbl_mach.config(text=f"{cond.mach:.4f}")
            self.lbl_rho.config(text=f"{cond.rho:.4f}")
            self.lbl_area.config(text=f"{cfg['wing_area_m2']:.2f} m²")
            if cfg["search_mode"] == "payload":
                self.lbl_clreq.config(text=f"{cfg['required_cl']:.4f}")
            else:
                self.lbl_clreq.config(text=f"{cond.target_cl:.3f} (alvo)")
        except Exception:
            self.lbl_re.config(text="erro")

    def _ao_editar_3d(self):
        self._atualiza_dados()
        code = self.top4[self.selected_idx][0] if self.top4 else "2412"
        self._desenha_3d_preview(code)

    # ----------------------------------------------------------
    # EXECUÇÃO DA OTIMIZAÇÃO + PIPELINE AUTÔNOMA
    # ----------------------------------------------------------

    def _iniciar_analise(self):
        if self.analisando:
            return
        if not engine.XFOIL_PATH.exists():
            messagebox.showerror("xfoil.exe não encontrado", f"Coloque o xfoil.exe em:\n{engine.XFOIL_PATH}")
            return

        try:
            cond, cfg, w3d = self._monta_cond_cfg()
        except Exception as e:
            messagebox.showerror("Erro nos parâmetros", str(e))
            return

        self.analisando = True
        self.btn_calcular.config(state="disabled")
        self.progresso["value"] = 0
        self._set_badge("● OTIMIZANDO 2D...", COR["amarelo"])
        self.lbl_status.config(text="Executando XFOIL nos perfis NACA...")

        threading.Thread(
            target=self._thread_analise,
            args=(cond, cfg, w3d),
            daemon=True,
        ).start()
        self.root.after(80, self._checa_fila)

    def _thread_analise(self, cond, cfg, w3d):
        def _prog(done, total, code, _res):
            self.fila.put(("prog", done, total, code))

        try:
            best_code, result, top4 = optimizer.run(cond, cfg, progress_callback=_prog)
            self.fila.put(("ok", best_code, result, top4, cond, cfg, w3d))
        except Exception as e:
            self.fila.put(("erro", str(e)))

    def _checa_fila(self):
        try:
            while True:
                msg = self.fila.get_nowait()
                kind = msg[0]

                if kind == "prog":
                    _, done, total, code = msg
                    pct = (done / max(1, total)) * 100.0
                    self.progresso["value"] = pct
                    self.lbl_status.config(text=f"Testando NACA {code} ({done}/{total})...")
                elif kind == "erro":
                    self.analisando = False
                    self.btn_calcular.config(state="normal")
                    self._set_badge("● ERRO", COR["vermelho"])
                    self.lbl_status.config(text=f"Erro: {msg[1]}")
                    messagebox.showerror("Erro na análise", msg[1])
                    return
                elif kind == "ok":
                    _, best_code, result, top4, cond, cfg, w3d = msg
                    self.analisando = False
                    self.btn_calcular.config(state="normal")
                    if result is None or not top4:
                        self._set_badge("● SEM RESULTADO", COR["amarelo"])
                        self.lbl_status.config(text="Nenhum perfil passou nos filtros.")
                        messagebox.showwarning("Sem resultado", "Nenhum perfil passou nos filtros. Ajuste alpha, tolerância ou carga.")
                        return

                    self.top4 = top4
                    self.cond_atual = cond
                    self.cfg_atual = cfg
                    self._atualiza_cards_top4()
                    self._selecionar_asa(0)
                    self.progresso["value"] = 100
                    self.lbl_status.config(text=f"Concluído! Melhor: NACA {best_code}")

                    if self.auto_pipeline.get():
                        self._executar_pipeline_3d(0, w3d)
                    else:
                        self._set_badge("● CONCLUÍDO", COR["verde"])
                    return
                elif kind == "3d_log":
                    self.lbl_log.config(text=msg[1])
                elif kind == "3d_done":
                    _, ok, out_msg = msg
                    self.gerando_3d = False
                    self.btn_3d.config(state="normal")
                    if ok:
                        self._set_badge("● PIPELINE CONCLUÍDA", COR["verde"])
                        self.lbl_log.config(text=out_msg)
                    else:
                        self._set_badge("● AVISO 3D", COR["amarelo"])
                        self.lbl_log.config(text=out_msg)
                    return
        except queue.Empty:
            pass

        if self.analisando or self.gerando_3d:
            self.root.after(80, self._checa_fila)

    # ----------------------------------------------------------
    # TOP 4 & VISUALIZAÇÃO EM TEMPO REAL
    # ----------------------------------------------------------

    def _atualiza_cards_top4(self):
        for i in range(4):
            w = self.top4_widgets[i]
            if i < len(self.top4):
                code, res = self.top4[i]
                w["code"].config(text=f"NACA {code}")
                w["eff"].config(text=f"CL/CD {res['efficiency']:.1f}")
                lift_txt = f" | {res['lift_kg']:.0f} kgf" if "lift_kg" in res else ""
                w["meta"].config(text=f"CL {res['cl']:.3f} | CD {res['cd']:.4f} | α {res['alpha_opt']:.1f}°{lift_txt}")
            else:
                w["code"].config(text="—")
                w["eff"].config(text="CL/CD: —")
                w["meta"].config(text="Sem candidato")

    def _selecionar_asa(self, idx: int):
        if idx >= len(self.top4):
            return
        self.selected_idx = idx

        for i, w in enumerate(self.top4_widgets):
            is_sel = (i == idx)
            bg = COR["card_active"] if is_sel else COR["card"]
            border = COR["azul"] if is_sel else COR["borda"]
            w["card"].config(bg=bg, highlightbackground=border, highlightthickness=2 if is_sel else 1)
            w["hdr"].config(bg=bg)
            w["rank"].config(bg=bg)
            w["tag"].config(bg=bg, text="SELECIONADA" if is_sel else "")
            w["code"].config(bg=bg)
            w["eff"].config(bg=bg)
            w["meta"].config(bg=bg)

        code, res = self.top4[idx]
        self.kpi_labels["code"].config(text=f"NACA {code}", fg=COR["azul"])
        self.kpi_labels["cl"].config(text=f"{res['cl']:.4f}")
        self.kpi_labels["cd"].config(text=f"{res['cd']:.5f}")
        self.kpi_labels["eff"].config(text=f"{res['efficiency']:.2f}", fg=COR["verde"])
        self.kpi_labels["alpha"].config(text=f"{res['alpha_opt']:.1f}°")
        if "lift_kg" in res:
            self.kpi_labels["lift"].config(text=f"{res['lift_kg']:.1f} kgf")
        else:
            self.kpi_labels["lift"].config(text="Modo CL")

        x, y = engine.nacaGenerator(code, n_points=255)
        self._desenha_perfil_2d(x, y, code, res)
        self._desenha_3d_preview(code)

    def _desenha_perfil_2d(self, x, y, code: str, res: dict):
        self.ax_2d.clear()
        self.ax_2d.set_facecolor(COR["bg"])
        self.ax_2d.plot(x, y, color=COR["azul"], linewidth=2.0, label=f"NACA {code}")
        self.ax_2d.fill(x, y, alpha=0.18, color=COR["azul"])
        self.ax_2d.axhline(0, color=COR["borda"], linewidth=0.8, linestyle="--")
        self.ax_2d.set_aspect("equal")
        self.ax_2d.grid(True, alpha=0.2, color=COR["borda"])
        self.ax_2d.tick_params(colors=COR["texto_sec"], labelsize=8)
        for sp in self.ax_2d.spines.values():
            sp.set_edgecolor(COR["borda"])
        self.ax_2d.set_title(
            f"NACA {code}  |  CL={res['cl']:.3f}  CD={res['cd']:.4f}  CL/CD={res['efficiency']:.1f}  α={res['alpha_opt']:.1f}°",
            color=COR["texto"], fontsize=9, pad=8
        )
        self.fig_2d.tight_layout()
        self.canvas_2d.draw()

    def _limpa_grafico_2d(self):
        self.ax_2d.clear()
        self.ax_2d.set_facecolor(COR["bg"])
        self.ax_2d.text(
            0.5, 0.5, "Execute a otimização para visualizar o perfil 2D",
            transform=self.ax_2d.transAxes, ha="center", va="center",
            color=COR["texto_dim"], fontsize=9
        )
        self.ax_2d.set_xticks([])
        self.ax_2d.set_yticks([])
        self.canvas_2d.draw()

    def _desenha_3d_preview(self, code: str):
        try:
            w3d = self._le_wing_3d()
            x, y = engine.nacaGenerator(code, n_points=120)
            Xg, Yg, Zg = pipeline.build_wing_preview_mesh(x, y, w3d, n_sections=14, n_profile_pts=60)

            self.ax_3d.clear()
            self.ax_3d.set_facecolor(COR["bg"])
            # Plota asa com envergadura no eixo Y visual e espessura no Z visual para melhor leitura 3D
            self.ax_3d.plot_surface(
                Xg, Zg, Yg,
                color=COR["azul"], alpha=0.85, edgecolor="#0F2A3F", linewidth=0.25, antialiased=True
            )
            self.ax_3d.set_xlabel("Corda X (mm)", color=COR["texto_sec"], fontsize=8)
            self.ax_3d.set_ylabel("Envergadura Z (mm)", color=COR["texto_sec"], fontsize=8)
            self.ax_3d.set_zlabel("Espessura/Diedro Y (mm)", color=COR["texto_sec"], fontsize=8)
            self.ax_3d.tick_params(colors=COR["texto_dim"], labelsize=7)
            self.ax_3d.set_title(f"Asa 3D — NACA {code} (Tempo Real)", color=COR["texto"], fontsize=9)

            max_range = max(Xg.max() - Xg.min(), Zg.max() - Zg.min(), 1.0) / 2.0
            mid_x = (Xg.max() + Xg.min()) / 2.0
            mid_z = (Zg.max() + Zg.min()) / 2.0
            mid_y = (Yg.max() + Yg.min()) / 2.0
            self.ax_3d.set_xlim(mid_x - max_range, mid_x + max_range)
            self.ax_3d.set_ylim(mid_z - max_range, mid_z + max_range)
            self.ax_3d.set_zlim(mid_y - max_range * 0.4, mid_y + max_range * 0.4)
            self.ax_3d.view_init(elev=26, azim=-48)
            self.canvas_3d.draw()
        except Exception:
            pass

    # ----------------------------------------------------------
    # EXPORTAÇÃO & PIPELINE 3D PARA A ASA SELECIONADA
    # ----------------------------------------------------------

    def _exportar(self, tipo: str):
        if not self.top4 or self.cond_atual is None:
            messagebox.showwarning("Sem resultado", "Execute a otimização antes de exportar.")
            return

        code, res = self.top4[self.selected_idx]
        x, y = engine.nacaGenerator(code, n_points=255)

        if tipo == "all":
            pasta = filedialog.askdirectory(title="Escolha a pasta de exportação")
            if not pasta:
                return
            out = Path(pasta)
            dat_p = engine.export_dat(x, y, code, out)
            engine.export_svg(x, y, code, out)
            engine.export_json(code, res, self.cond_atual, dat_p, out, extra_cfg=self.cfg_atual)
            engine.export_plot(x, y, code, res, out)
            messagebox.showinfo("Exportado!", f"Pacote 2D completo de NACA {code} salvo em:\n{out}")
            return

        ext_map = {"svg": [("SVG", "*.svg")], "dat": [("DAT", "*.dat")], "json": [("JSON", "*.json")]}
        def_map = {"svg": f"naca_{code}.svg", "dat": f"naca_{code}.dat", "json": f"naca_{code}_result.json"}
        caminho = filedialog.asksaveasfilename(defaultextension=f".{tipo}", filetypes=ext_map[tipo], initialfile=def_map[tipo])
        if not caminho:
            return
        out = Path(caminho).parent
        if tipo == "svg":
            engine.export_svg(x, y, code, out)
        elif tipo == "dat":
            engine.export_dat(x, y, code, out)
        elif tipo == "json":
            engine.export_json(code, res, self.cond_atual, Path(f"naca_{code}.dat"), out, extra_cfg=self.cfg_atual)
        messagebox.showinfo("Exportado!", f"NACA {code} salvo em:\n{caminho}")

    def _gerar_3d_selecionada(self):
        if not self.top4 or self.cond_atual is None:
            messagebox.showwarning("Sem asa selecionada", "Execute a otimização e selecione uma das 4 asas primeiro.")
            return
        self._executar_pipeline_3d(self.selected_idx, self._le_wing_3d())

    def _executar_pipeline_3d(self, idx: int, w3d: pipeline.Wing3DParams):
        if self.gerando_3d:
            return
        code, res = self.top4[idx]
        out = pipeline.DEFAULT_OUTPUT_DIR
        out.mkdir(exist_ok=True)
        x, y = engine.nacaGenerator(code, n_points=255)
        dat_path = engine.export_dat(x, y, code, out)
        engine.export_svg(x, y, code, out)
        engine.export_json(code, res, self.cond_atual, dat_path, out, extra_cfg=self.cfg_atual)
        stl_path = out / f"wing_naca_{code}.stl"

        self.gerando_3d = True
        self.btn_3d.config(state="disabled")
        self._set_badge("● GERANDO STL 3D...", COR["amarelo"])
        self.lbl_log.config(text=f"[Pipeline] Iniciando geração 3D para NACA {code}...")

        def _worker():
            ok, _stl, msg = pipeline.run_3d_generator(
                dat_path, stl_path, w3d,
                log_callback=lambda line: self.fila.put(("3d_log", line)),
            )
            self.fila.put(("3d_done", ok, msg))

        threading.Thread(target=_worker, daemon=True).start()
        self.root.after(80, self._checa_fila)

    def _set_badge(self, txt: str, cor: str):
        self.badge_pipeline.config(text=txt, fg=cor)

    def _resetar_padrao(self):
        for k, v in [("altitude", "1500"), ("velocity", "60"), ("payload_kg", "120"), ("target_cl", "0.8")]:
            self.vars_voo[k].set(v)
        for k, v in [
            ("span_mm", "5000"), ("root_chord_mm", "1200"), ("tip_chord_mm", "700"),
            ("wing_sweep_deg", "15"), ("tip_twist_deg", "-3"), ("wing_dihedral_deg", "2"),
            ("section_size_mm", "250"), ("voxel_size_mm", "2.5"),
        ]:
            self.vars_3d[k].set(v)
        for k, v in [
            ("cl_tolerance", "0.15"), ("camber_max", "6"), ("espessuras", "8,10,12,15,18"),
            ("alpha_start", "-2"), ("alpha_end", "12"), ("alpha_step", "0.5"),
            ("n_panels", "240"), ("n_iterations", "100"), ("n_threads", "4"),
        ]:
            self.vars_busca[k].set(v)
        self.vars_filtros["cd_min"].set("0")
        self.vars_filtros["eff_max"].set("0")
        self._atualiza_dados()
        self.lbl_status.config(text="Padrões restaurados.")

    def _ao_fechar(self):
        if self.analisando or self.gerando_3d:
            if not messagebox.askyesno("Processo em andamento", "Uma etapa da pipeline está em execução. Deseja fechar?"):
                return
        plt.close("all")
        self.root.destroy()


def main():
    root = tk.Tk()
    WingLabsGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
