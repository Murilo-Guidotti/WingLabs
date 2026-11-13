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

from winglabs.aero import optimizer
from winglabs.aero import xfoil_engine as engine
from winglabs.core import environment as env
from winglabs.core import pipeline


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
    "texto_sec":    "#B0BECF",
    "texto_dim":    "#8E9AAF",
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
        self.cancel_event = threading.Event()
        self._resetando = False
        self._debounce_3d_id: str | None = None
        self.avancado_aberto = False
        self.entries: dict[str, tk.Entry] = {}

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
        self.root.minsize(1100, 680)
        self.root.configure(bg=COR["bg"])
        self.root.protocol("WM_DELETE_WINDOW", self._ao_fechar)
        self.root.bind("<Control-Return>", lambda _e: self._iniciar_analise())
        self.root.bind("<Escape>", lambda _e: self._cancelar_analise())

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
            padding=(12, 8),
            borderwidth=0,
            focusthickness=1,
            focuscolor=COR["texto"],
        )
        style.map(
            "Primary.TButton",
            background=[("active", COR["azul_hover"]), ("disabled", COR["borda"])],
            foreground=[("disabled", COR["texto_sec"])],
        )
        style.configure(
            "Accent.TButton",
            background=COR["verde"],
            foreground="#062016",
            font=FONTE["botao"],
            padding=(12, 8),
            borderwidth=0,
            focusthickness=1,
            focuscolor=COR["texto"],
        )
        style.map(
            "Accent.TButton",
            background=[("active", "#10B981"), ("disabled", COR["borda"])],
            foreground=[("disabled", COR["texto_sec"])],
        )
        style.configure(
            "Ghost.TButton",
            background=COR["card"],
            foreground=COR["texto"],
            bordercolor=COR["borda"],
            lightcolor=COR["borda"],
            darkcolor=COR["borda"],
            focuscolor=COR["azul"],
            font=FONTE["sec"],
            padding=(10, 6),
            borderwidth=1,
        )
        style.map(
            "Ghost.TButton",
            background=[("active", COR["card_hover"])],
            bordercolor=[("active", COR["azul_dim"])],
        )

        style.configure(
            "Wing.Horizontal.TProgressbar",
            background=COR["azul"],
            troughcolor=COR["surface"],
            bordercolor=COR["borda"],
            lightcolor=COR["azul"],
            darkcolor=COR["azul"],
            borderwidth=0,
            thickness=6,
        )
        style.configure(
            "Vertical.TScrollbar",
            background=COR["borda"],
            troughcolor=COR["sidebar"],
            bordercolor=COR["sidebar"],
            arrowcolor=COR["texto_sec"],
            lightcolor=COR["borda"],
            darkcolor=COR["borda"],
            gripcount=0,
            width=10,
        )
        style.map(
            "Vertical.TScrollbar",
            background=[("active", COR["azul_dim"]), ("pressed", COR["azul"])],
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

        # Corpo principal: Sidebar esquerda + Área de trabalho direita (sem espaçamento externo/interno)
        self.body = tk.Frame(self.root, bg=COR["bg"])
        self.body.pack(fill="both", expand=True, padx=0, pady=0)

        self.sidebar = tk.Frame(
            self.body, bg=COR["sidebar"], width=340,
            highlightbackground=COR["borda"], highlightthickness=1
        )
        self.sidebar.pack(side="left", fill="y", padx=0, pady=0)
        self.sidebar.pack_propagate(False)

        self.workspace = tk.Frame(self.body, bg=COR["bg"])
        self.workspace.pack(side="left", fill="both", expand=True, padx=0, pady=0)

        self._cria_sidebar()
        self._cria_workspace()

    # ----------------------------------------------------------
    # SIDEBAR ESQUERDA (INPUTS & PIPELINE)
    # ----------------------------------------------------------

    def _cria_sidebar(self):
        # Rodapé fixo da Sidebar (sempre visível mesmo em telas menores)
        act_divider = tk.Frame(self.sidebar, bg=COR["borda"], height=1)
        act_divider.pack(side="bottom", fill="x")

        act_box = tk.Frame(self.sidebar, bg=COR["sidebar"], padx=10, pady=6)
        act_box.pack(side="bottom", fill="x")

        tk.Checkbutton(
            act_box,
            text="Pipeline autônoma: gerar STL 3D ao concluir",
            variable=self.auto_pipeline,
            bg=COR["sidebar"], fg=COR["texto_sec"],
            selectcolor=COR["card"], activebackground=COR["sidebar"],
            activeforeground=COR["texto"], font=FONTE["pequena"],
        ).pack(anchor="w", pady=(0, 4))

        self.btn_calcular = ttk.Button(
            act_box, text="▶  EXECUTAR OTIMIZAÇÃO (Ctrl+Enter)",
            style="Primary.TButton", command=self._iniciar_analise
        )
        self.btn_calcular.pack(fill="x", pady=(0, 4))

        ttk.Button(
            act_box, text="↺  Restaurar padrões",
            style="Ghost.TButton", command=self._resetar_padrao
        ).pack(fill="x")

        self.progresso = ttk.Progressbar(
            act_box, style="Wing.Horizontal.TProgressbar", mode="determinate", maximum=100
        )
        self.progresso.pack(fill="x", pady=(6, 2))
        self.lbl_status = tk.Label(
            act_box, text="Pronto para iniciar.", bg=COR["sidebar"],
            fg=COR["texto_dim"], font=FONTE["pequena"], anchor="w"
        )
        self.lbl_status.pack(fill="x")

        # Área rolável superior de inputs
        scroll_container = tk.Frame(self.sidebar, bg=COR["sidebar"])
        scroll_container.pack(side="top", fill="both", expand=True)

        self.canvas_sb = tk.Canvas(scroll_container, bg=COR["sidebar"], highlightthickness=0)
        sb = ttk.Scrollbar(scroll_container, orient="vertical", command=self.canvas_sb.yview, style="Vertical.TScrollbar")
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
        seg.pack(fill="x", padx=10, pady=(4, 5))

        self.btn_modo_payload = tk.Button(
            seg, text="Carga / Peso (kg)", relief="flat", cursor="hand2",
            font=FONTE["sec"], pady=4,
            command=lambda: self._set_modo("payload"),
        )
        self.btn_modo_payload.pack(side="left", fill="x", expand=True, padx=(0, 3))

        self.btn_modo_cl = tk.Button(
            seg, text="CL Alvo Fixo", relief="flat", cursor="hand2",
            font=FONTE["sec"], pady=4,
            command=lambda: self._set_modo("target_cl"),
        )
        self.btn_modo_cl.pack(side="left", fill="x", expand=True, padx=(3, 0))

        # Cenário de Voo
        self.vars_voo: dict[str, tk.StringVar] = {}
        card_voo = self._card(p, "CENÁRIO DE VOO")
        grid_voo = tk.Frame(card_voo, bg=COR["card"])
        grid_voo.pack(fill="x", padx=10, pady=(4, 2))
        grid_voo.columnconfigure(0, weight=1)
        grid_voo.columnconfigure(1, weight=1)

        for idx_v, (key, label, default) in enumerate([("altitude", "Altitude (m)", "1500"), ("velocity", "Velocidade (m/s)", "60")]):
            cell = tk.Frame(grid_voo, bg=COR["card"])
            cell.grid(row=0, column=idx_v, sticky="ew", padx=3, pady=2)
            tk.Label(cell, text=label, bg=COR["card"], fg=COR["texto_sec"], font=FONTE["pequena"]).pack(anchor="w")
            var = tk.StringVar(value=default)
            var.trace_add("write", lambda *_: self._atualiza_dados())
            ent = tk.Entry(
                cell, textvariable=var, bg=COR["bg"], fg=COR["texto"],
                insertbackground=COR["azul"], font=FONTE["entrada"], relief="flat", bd=3,
                highlightthickness=1, highlightbackground=COR["borda"], highlightcolor=COR["azul"]
            )
            ent.pack(fill="x", pady=(2, 0))
            self.vars_voo[key] = var
            self.entries[key] = ent

        self.frame_payload_input = tk.Frame(card_voo, bg=COR["card"])
        self._campo(self.frame_payload_input, "payload_kg", "Peso da Carga / Massa (kg)", "120", self.vars_voo, self._atualiza_dados)

        self.frame_cl_input = tk.Frame(card_voo, bg=COR["card"])
        self._campo(self.frame_cl_input, "target_cl", "CL Alvo", "0.8", self.vars_voo, self._atualiza_dados)

        # Resumo Atmosférico + CL Requerido ao vivo (sempre abaixo dos inputs de voo)
        self.atm_box = tk.Frame(card_voo, bg=COR["surface"], padx=8, pady=4)
        self.atm_box.pack(fill="x", padx=10, pady=(3, 5))
        self.lbl_re   = self._mini_kv(self.atm_box, "Reynolds", "—")
        self.lbl_mach = self._mini_kv(self.atm_box, "Mach", "—")
        self.lbl_rho  = self._mini_kv(self.atm_box, "ρ Ar (kg/m³)", "—")
        self.lbl_area = self._mini_kv(self.atm_box, "Área Alar S", "—")
        self.lbl_clreq = self._mini_kv(self.atm_box, "CL Mín. Carga", "—", COR["verde"])

        # Geometria 3D da Asa (Tempo real + Módulo 2)
        self.vars_3d: dict[str, tk.StringVar] = {}
        card_3d = self._card(p, "GEOMETRIA 3D DA ASA (MÓDULO 2)")
        grid3d = tk.Frame(card_3d, bg=COR["card"])
        grid3d.pack(fill="x", padx=10, pady=(2, 5))
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
            cell.grid(row=r, column=c, sticky="ew", padx=3, pady=2)
            tk.Label(cell, text=label, bg=COR["card"], fg=COR["texto_sec"], font=FONTE["pequena"]).pack(anchor="w")
            var = tk.StringVar(value=default)
            var.trace_add("write", lambda *_: self._ao_editar_3d())
            ent = tk.Entry(
                cell, textvariable=var, bg=COR["bg"], fg=COR["texto"],
                insertbackground=COR["azul"], font=FONTE["entrada"], relief="flat", bd=3,
                highlightthickness=1, highlightbackground=COR["borda"], highlightcolor=COR["azul"]
            )
            ent.pack(fill="x", pady=(2, 0))
            self.vars_3d[key] = var
            self.entries[key] = ent

        # Busca & XFOIL (Seção recolhível para reduzir carga cognitiva inicial)
        self.vars_busca: dict[str, tk.StringVar] = {}
        outer_busca = tk.Frame(p, bg=COR["borda"])
        outer_busca.pack(fill="x", padx=0, pady=0)
        card_busca = tk.Frame(outer_busca, bg=COR["card"])
        card_busca.pack(fill="x", padx=0, pady=(0, 1))

        hdr_busca = tk.Frame(card_busca, bg=COR["card"], cursor="hand2")
        hdr_busca.pack(fill="x")
        self.lbl_toggle_busca = tk.Label(
            hdr_busca, text="▸  BUSCA & XFOIL (AVANÇADO)", bg=COR["card"], fg=COR["azul"],
            font=FONTE["pequena"], padx=10, pady=6, cursor="hand2"
        )
        self.lbl_toggle_busca.pack(side="left")
        self.lbl_resumo_busca = tk.Label(
            hdr_busca, text="α -2°..12° · 240p", bg=COR["card"], fg=COR["texto_dim"],
            font=FONTE["pequena"], padx=8, cursor="hand2"
        )
        self.lbl_resumo_busca.pack(side="right")
        for w_hdr in (hdr_busca, self.lbl_toggle_busca, self.lbl_resumo_busca):
            w_hdr.bind("<Button-1>", lambda _e: self._toggle_avancado())

        tk.Frame(card_busca, bg=COR["borda"], height=1).pack(fill="x", padx=10)

        self.body_busca = tk.Frame(card_busca, bg=COR["card"])

        g_b = tk.Frame(self.body_busca, bg=COR["card"])
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
            var.trace_add("write", lambda *_: self._atualiza_dados())
            ent = tk.Entry(
                cell, textvariable=var, bg=COR["bg"], fg=COR["texto"],
                insertbackground=COR["azul"], font=FONTE["entrada"], relief="flat", bd=3,
                highlightthickness=1, highlightbackground=COR["borda"], highlightcolor=COR["azul"]
            )
            ent.pack(fill="x", pady=(2, 0))
            self.vars_busca[key] = var
            self.entries[key] = ent

        self._campo(self.body_busca, "espessuras", "Espessuras (%)", "8,10,12,15,18", self.vars_busca, self._atualiza_dados)

        self.vars_filtros: dict[str, tk.StringVar] = {}
        g_f = tk.Frame(self.body_busca, bg=COR["card"])
        g_f.pack(fill="x", padx=10, pady=(2, 8))
        g_f.columnconfigure(0, weight=1)
        g_f.columnconfigure(1, weight=1)
        for idx_f, (key, label, default) in enumerate([("cd_min", "CD mín (0=auto)", "0"), ("eff_max", "CL/CD máx (0=auto)", "0")]):
            cell = tk.Frame(g_f, bg=COR["card"])
            cell.grid(row=0, column=idx_f, sticky="ew", padx=3)
            tk.Label(cell, text=label, bg=COR["card"], fg=COR["texto_sec"], font=FONTE["pequena"]).pack(anchor="w")
            var = tk.StringVar(value=default)
            var.trace_add("write", lambda *_: self._atualiza_dados())
            ent = tk.Entry(
                cell, textvariable=var, bg=COR["bg"], fg=COR["texto"],
                insertbackground=COR["azul"], font=FONTE["entrada"], relief="flat", bd=3,
                highlightthickness=1, highlightbackground=COR["borda"], highlightcolor=COR["azul"]
            )
            ent.pack(fill="x", pady=(2, 0))
            self.vars_filtros[key] = var
            self.entries[key] = ent

        self._bind_mousewheel(self.frame_sb)

    # ----------------------------------------------------------
    # WORKSPACE DIREITA (TOP 4 CARDS + 2D/3D TEMPO REAL + EXPORTS)
    # ----------------------------------------------------------

    def _cria_workspace(self):
        w = self.workspace

        # 1) Barra Top 4 Asas Selecionáveis (janelas encostadas sem espaçamento)
        self.top_hdr = tk.Frame(
            w, bg=COR["surface"], highlightbackground=COR["borda"],
            highlightthickness=1, padx=12, pady=5
        )
        self.top_hdr.pack(fill="x", padx=0, pady=0)
        tk.Label(
            self.top_hdr,
            text="TOP 4 MELHORES ASAS — Clique ou use Tab + Enter para visualizar em tempo real e exportar",
            bg=COR["surface"], fg=COR["texto_sec"], font=FONTE["sec"]
        ).pack(side="left")

        self.cards_frame = tk.Frame(w, bg=COR["bg"])
        self.cards_frame.pack(fill="x", padx=0, pady=0)
        self.top4_widgets: list[dict] = []

        for i in range(4):
            self.cards_frame.columnconfigure(i, weight=1, uniform="top4")
            card = tk.Frame(
                self.cards_frame, bg=COR["card"], highlightbackground=COR["borda"],
                highlightcolor=COR["azul"], highlightthickness=1, padx=12, pady=8,
                cursor="hand2", takefocus=1
            )
            card.grid(row=0, column=i, sticky="nsew", padx=0, pady=0)

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

            card.bind("<Return>", lambda e, idx=i: self._selecionar_asa(idx))
            card.bind("<space>", lambda e, idx=i: self._selecionar_asa(idx))
            for widget in (card, hdr_row, lbl_rank, lbl_tag, lbl_code, lbl_eff, lbl_meta):
                widget.bind("<Button-1>", lambda e, idx=i: self._selecionar_asa(idx))
                widget.bind("<Enter>", lambda e, idx=i: self._hover_card(idx, True))
                widget.bind("<Leave>", lambda e, idx=i: self._hover_card(idx, False))

            self.top4_widgets.append({
                "card": card, "hdr": hdr_row, "rank": lbl_rank,
                "tag": lbl_tag, "code": lbl_code, "eff": lbl_eff, "meta": lbl_meta
            })

        # 2) Viewport Split: 2D Airfoil (Esquerda) + 3D Wing Real-Time (Direita)
        self.view_frame = tk.Frame(w, bg=COR["bg"])
        self.view_frame.pack(fill="both", expand=True, padx=0, pady=0)
        self.view_frame.columnconfigure(0, weight=1, uniform="view")
        self.view_frame.columnconfigure(1, weight=1, uniform="view")
        self.view_frame.rowconfigure(0, weight=1)

        # Painel 2D
        self.p2d = tk.Frame(self.view_frame, bg=COR["bg"], highlightbackground=COR["borda"], highlightthickness=1)
        self.p2d.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        hdr_2d = tk.Frame(self.p2d, bg=COR["surface"])
        hdr_2d.pack(fill="x")
        tk.Label(
            hdr_2d, text="  PERFIL 2D & LINHA DE CAMBER (XFOIL)",
            bg=COR["surface"], fg=COR["azul"], font=FONTE["sec"], pady=5
        ).pack(anchor="w")
        tk.Frame(self.p2d, bg=COR["borda"], height=1).pack(fill="x")

        self.fig_2d, self.ax_2d = plt.subplots(figsize=(5.5, 3.6), facecolor=COR["bg"])
        self.canvas_2d = FigureCanvasTkAgg(self.fig_2d, master=self.p2d)
        self.w2d = self.canvas_2d.get_tk_widget()
        self.w2d.configure(bg=COR["bg"], highlightthickness=0, bd=0)
        self.w2d.pack(fill="both", expand=True, padx=0, pady=0)
        self._limpa_grafico_2d()

        # Painel 3D
        self.p3d = tk.Frame(self.view_frame, bg=COR["bg"], highlightbackground=COR["borda"], highlightthickness=1)
        self.p3d.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
        hdr_3d = tk.Frame(self.p3d, bg=COR["surface"])
        hdr_3d.pack(fill="x")
        tk.Label(
            hdr_3d, text="  ASA 3D EM TEMPO REAL (Arraste para girar)",
            bg=COR["surface"], fg=COR["azul"], font=FONTE["sec"], pady=5
        ).pack(anchor="w")
        tk.Frame(self.p3d, bg=COR["borda"], height=1).pack(fill="x")

        self.fig_3d = plt.figure(figsize=(5.5, 3.6), facecolor=COR["bg"])
        self.ax_3d = self.fig_3d.add_subplot(111, projection="3d")
        self.canvas_3d = FigureCanvasTkAgg(self.fig_3d, master=self.p3d)
        self.w3d = self.canvas_3d.get_tk_widget()
        self.w3d.configure(bg=COR["bg"], highlightthickness=0, bd=0)
        self.w3d.pack(fill="both", expand=True, padx=0, pady=0)

        # 3) Barra Inferior: KPIs da Asa Selecionada + Botões de Exportação & Pipeline 3D
        self.bottom_panel = tk.Frame(
            w, bg=COR["surface"], highlightbackground=COR["borda"],
            highlightthickness=1, padx=0, pady=0
        )
        self.bottom_panel.pack(fill="x", padx=0, pady=0)

        self.kpi_bar = tk.Frame(self.bottom_panel, bg=COR["surface"])
        self.kpi_bar.pack(fill="x", padx=0, pady=0)
        self.kpi_labels: dict[str, tk.Label] = {}
        self.kpi_boxes: list[tk.Frame] = []
        kpi_defs = [
            ("Asa Selecionada", "code"),
            ("CL", "cl"),
            ("CD", "cd"),
            ("Eficiência CL/CD", "eff"),
            ("Ângulo α", "alpha"),
            ("Sustentação", "lift"),
        ]
        for idx_k, (title, key) in enumerate(kpi_defs):
            self.kpi_bar.columnconfigure(idx_k, weight=1, uniform="kpi")
            box = tk.Frame(
                self.kpi_bar, bg=COR["card"], highlightbackground=COR["borda"],
                highlightthickness=1, padx=10, pady=5
            )
            box.grid(row=0, column=idx_k, sticky="nsew", padx=0, pady=0)
            tk.Label(box, text=title, bg=COR["card"], fg=COR["texto_dim"], font=FONTE["pequena"]).pack(anchor="w")
            lbl = tk.Label(box, text="—", bg=COR["card"], fg=COR["texto"], font=FONTE["kpi"])
            lbl.pack(anchor="w")
            self.kpi_labels[key] = lbl
            self.kpi_boxes.append(box)

        footer_ctrl = tk.Frame(self.bottom_panel, bg=COR["surface"], padx=10, pady=8)
        footer_ctrl.pack(fill="x", padx=0, pady=0)

        btn_bar = tk.Frame(footer_ctrl, bg=COR["surface"])
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
            footer_ctrl, text="Pipeline: selecione uma asa ou execute a otimização.",
            bg=COR["surface"], fg=COR["texto_sec"], font=FONTE["mono"], anchor="w"
        )
        self.lbl_log.pack(fill="x", pady=(6, 0))

    # ----------------------------------------------------------
    # HELPERS DE UI
    # ----------------------------------------------------------

    def _card(self, parent, titulo: str) -> tk.Frame:
        outer = tk.Frame(parent, bg=COR["borda"])
        outer.pack(fill="x", padx=0, pady=0)
        inner = tk.Frame(outer, bg=COR["card"])
        inner.pack(fill="x", padx=0, pady=(0, 1))
        tk.Label(
            inner, text=titulo, bg=COR["card"], fg=COR["azul"],
            font=FONTE["pequena"], padx=10, pady=4
        ).pack(anchor="w")
        tk.Frame(inner, bg=COR["borda"], height=1).pack(fill="x", padx=10)
        return inner

    def _campo(self, parent, key: str, label: str, padrao: str, dic: dict, on_change=None):
        tk.Label(parent, text=label, bg=COR["card"], fg=COR["texto_sec"], font=FONTE["pequena"]).pack(anchor="w", padx=10, pady=(4, 0))
        var = tk.StringVar(value=padrao)
        if on_change:
            var.trace_add("write", lambda *_: on_change())
        ent = tk.Entry(
            parent, textvariable=var, bg=COR["bg"], fg=COR["texto"],
            insertbackground=COR["azul"], font=FONTE["entrada"], relief="flat", bd=3,
            highlightthickness=1, highlightbackground=COR["borda"], highlightcolor=COR["azul"]
        )
        ent.pack(fill="x", padx=10, pady=(2, 4))
        dic[key] = var
        self.entries[key] = ent

    def _mini_kv(self, parent, k: str, v: str, color: str = COR["azul"]) -> tk.Label:
        row = tk.Frame(parent, bg=COR["surface"])
        row.pack(fill="x", pady=1)
        tk.Label(row, text=f"{k}:", bg=COR["surface"], fg=COR["texto_sec"], font=FONTE["pequena"]).pack(side="left")
        lbl = tk.Label(row, text=v, bg=COR["surface"], fg=color, font=FONTE["mono"])
        lbl.pack(side="right")
        return lbl

    def _on_mousewheel(self, event):
        bbox = self.canvas_sb.bbox("all")
        if bbox and (bbox[3] - bbox[1]) > self.canvas_sb.winfo_height():
            self.canvas_sb.yview_scroll(-1 * (event.delta // 120), "units")

    def _bind_mousewheel(self, widget):
        widget.bind("<MouseWheel>", self._on_mousewheel)
        for child in widget.winfo_children():
            self._bind_mousewheel(child)

    def _toggle_avancado(self):
        self.avancado_aberto = not self.avancado_aberto
        if self.avancado_aberto:
            self.lbl_toggle_busca.config(text="▾  BUSCA & XFOIL (AVANÇADO)")
            self.body_busca.pack(fill="x")
            self._bind_mousewheel(self.body_busca)
        else:
            self.lbl_toggle_busca.config(text="▸  BUSCA & XFOIL (AVANÇADO)")
            self.body_busca.pack_forget()

    def _hover_card(self, idx: int, entering: bool):
        if idx >= len(self.top4_widgets):
            return
        is_sel = (idx < len(self.top4) and idx == self.selected_idx)
        if is_sel:
            return
        bg = COR["card_hover"] if entering else COR["card"]
        border = COR["azul_dim"] if entering else COR["borda"]
        w = self.top4_widgets[idx]
        w["card"].config(bg=bg, highlightbackground=border)
        for k in ("hdr", "rank", "tag", "code", "eff", "meta"):
            w[k].config(bg=bg)

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
            self.frame_payload_input.pack(fill="x", before=self.atm_box)
        else:
            self.btn_modo_cl.config(bg=COR["azul"], fg="#081018")
            self.btn_modo_payload.config(bg=COR["surface"], fg=COR["texto_sec"])
            self.frame_payload_input.pack_forget()
            self.frame_cl_input.pack(fill="x", before=self.atm_box)

    # ----------------------------------------------------------
    # LEITURA DE PARÂMETROS & CÁLCULOS AO VIVO
    # ----------------------------------------------------------

    def _marca_campo(self, key: str, valido: bool):
        ent = self.entries.get(key)
        if ent is not None:
            ent.config(highlightbackground=COR["borda"] if valido else COR["vermelho"])

    def _f(self, dic, key, default) -> float:
        raw = dic[key].get().strip().replace(",", ".")
        try:
            val = float(raw)
            self._marca_campo(key, True)
            return val
        except ValueError:
            self._marca_campo(key, False)
            return default

    def _i(self, dic, key, default) -> int:
        raw = dic[key].get().strip()
        try:
            val = int(raw)
            self._marca_campo(key, True)
            return val
        except ValueError:
            self._marca_campo(key, False)
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
        cond = env.FlightConditions(altitude=altitude, velocity=velocity, target_cl=0.8, chord_size=chord_m)

        if modo == "payload":
            req_cl = env.required_cl(payload_kg, cond.rho, velocity, area_m2)
            target_cl = req_cl
        else:
            target_cl = self._f(self.vars_voo, "target_cl", 0.8)
            req_cl = target_cl
        cond.target_cl = target_cl

        try:
            espessuras = [int(e.strip()) for e in self.vars_busca["espessuras"].get().split(",") if e.strip()]
            if not espessuras:
                espessuras = [8, 10, 12, 15, 18]
            self._marca_campo("espessuras", True)
        except ValueError:
            espessuras = [8, 10, 12, 15, 18]
            self._marca_campo("espessuras", False)

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
        if self._resetando:
            return
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
            self.lbl_resumo_busca.config(
                text=f"α {cfg['alpha_start']:.0f}°..{cfg['alpha_end']:.0f}° · {cfg['n_panels']}p"
            )
        except Exception:
            self.lbl_re.config(text="erro")

    def _ao_editar_3d(self):
        if self._resetando:
            return
        self._atualiza_dados()
        if self._debounce_3d_id is not None:
            self.root.after_cancel(self._debounce_3d_id)
        self._debounce_3d_id = self.root.after(180, self._dispara_preview_3d)

    def _dispara_preview_3d(self):
        self._debounce_3d_id = None
        code = self.top4[self.selected_idx][0] if self.top4 else "2412"
        self._desenha_3d_preview(code)

    # ----------------------------------------------------------
    # EXECUÇÃO DA OTIMIZAÇÃO + PIPELINE AUTÔNOMA
    # ----------------------------------------------------------

    def _cancelar_analise(self):
        if self.analisando:
            self.cancel_event.set()
            self.lbl_status.config(text="Cancelando otimização...")

    def _iniciar_analise(self):
        if self.analisando:
            self._cancelar_analise()
            return
        if self.gerando_3d:
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
        self.cancel_event.clear()
        self.btn_calcular.config(text="⏹  CANCELAR OTIMIZAÇÃO (Esc)")
        self.btn_3d.config(state="disabled")
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
            best_code, result, top4 = optimizer.run(
                cond, cfg, progress_callback=_prog, cancel_event=self.cancel_event
            )
            if self.cancel_event.is_set():
                self.fila.put(("cancelado",))
            else:
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
                elif kind == "cancelado":
                    self.analisando = False
                    self.btn_calcular.config(text="▶  EXECUTAR OTIMIZAÇÃO (Ctrl+Enter)", state="normal")
                    self.btn_3d.config(state="normal")
                    self._set_badge("● CANCELADO", COR["amarelo"])
                    self.lbl_status.config(text="Otimização cancelada pelo usuário.")
                    return
                elif kind == "erro":
                    self.analisando = False
                    self.btn_calcular.config(text="▶  EXECUTAR OTIMIZAÇÃO (Ctrl+Enter)", state="normal")
                    self.btn_3d.config(state="normal")
                    self._set_badge("● ERRO", COR["vermelho"])
                    self.lbl_status.config(text=f"Erro: {msg[1]}")
                    messagebox.showerror("Erro na análise", msg[1])
                    return
                elif kind == "ok":
                    _, best_code, result, top4, cond, cfg, w3d = msg
                    self.analisando = False
                    self.btn_calcular.config(text="▶  EXECUTAR OTIMIZAÇÃO (Ctrl+Enter)", state="normal")
                    self.btn_3d.config(state="normal")
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
        self.fig_2d.patch.set_facecolor(COR["bg"])
        self.ax_2d.set_facecolor(COR["bg"])
        self.ax_2d.plot(x, y, color=COR["azul"], linewidth=2.0, label=f"Perfil NACA {code}")
        self.ax_2d.fill(x, y, alpha=0.18, color=COR["azul"])

        # Linha de corda e linha de curvatura média (camber)
        self.ax_2d.plot([0.0, 1.0], [0.0, 0.0], color=COR["texto_dim"], linewidth=0.9, linestyle=":", label="Corda (x/c)")
        mid = len(x) // 2
        x_u, y_u = x[:mid + 1][::-1], y[:mid + 1][::-1]
        x_l, y_l = x[mid:], y[mid:]
        if len(x_u) == len(x_l):
            self.ax_2d.plot(
                (x_u + x_l) * 0.5, (y_u + y_l) * 0.5,
                color=COR["verde"], linewidth=1.2, linestyle="--", alpha=0.85, label="Linha de Camber"
            )

        t_pct = int(code[2:4])
        m_pct = int(code[0])
        p_dec = int(code[1]) * 10
        self.ax_2d.text(
            0.02, 0.92,
            f"Espessura máx: {t_pct}%  |  Camber: {m_pct}% em {p_dec}% c  |  Cm: {res.get('cm', 0.0):.3f}",
            transform=self.ax_2d.transAxes, color=COR["texto_sec"], fontsize=8
        )

        self.ax_2d.update_datalim([(-0.05, -0.25), (1.05, 0.28)])
        self.ax_2d.set_xlim(-0.05, 1.05)
        self.ax_2d.set_aspect("equal", adjustable="datalim")
        self.ax_2d.autoscale_view(scalex=False, scaley=True)
        self.ax_2d.grid(True, alpha=0.22, color=COR["borda"])
        self.ax_2d.set_xlabel("Posição ao longo da corda (x/c)", color=COR["texto_sec"], fontsize=8, labelpad=4)
        self.ax_2d.set_ylabel("Espessura (y/c)", color=COR["texto_sec"], fontsize=8, labelpad=2)
        self.ax_2d.tick_params(colors=COR["texto_dim"], labelsize=8)
        self.ax_2d.legend(loc="lower right", facecolor=COR["card"], edgecolor=COR["borda"], labelcolor=COR["texto_sec"], fontsize=7.5)
        for sp in self.ax_2d.spines.values():
            sp.set_visible(True)
            sp.set_edgecolor(COR["borda"])
        self.ax_2d.set_title(
            f"NACA {code}  |  CL={res['cl']:.3f}  CD={res['cd']:.4f}  CL/CD={res['efficiency']:.1f}  α={res['alpha_opt']:.1f}°",
            color=COR["texto"], fontsize=9, pad=8
        )
        self.fig_2d.subplots_adjust(left=0.12, right=0.97, top=0.90, bottom=0.13)
        self.canvas_2d.draw_idle()

    def _limpa_grafico_2d(self):
        self.ax_2d.clear()
        self.ax_2d.set_aspect("auto")
        self.fig_2d.patch.set_facecolor(COR["bg"])
        self.ax_2d.set_facecolor(COR["bg"])
        for sp in self.ax_2d.spines.values():
            sp.set_visible(False)
        self.ax_2d.text(
            0.5, 0.52, "Execute a otimização (Ctrl+Enter) para analisar os perfis 2D",
            transform=self.ax_2d.transAxes, ha="center", va="center",
            color=COR["texto_sec"], fontsize=9, fontweight="bold"
        )
        self.ax_2d.text(
            0.5, 0.42, "Os 4 melhores aerofólios segundo CL/CD serão exibidos nos cards acima",
            transform=self.ax_2d.transAxes, ha="center", va="center",
            color=COR["texto_dim"], fontsize=8
        )
        self.ax_2d.set_xticks([])
        self.ax_2d.set_yticks([])
        self.fig_2d.subplots_adjust(left=0.0, right=1.0, top=1.0, bottom=0.0)
        self.canvas_2d.draw_idle()

    def _estiliza_eixo_3d(self):
        for axis in (self.ax_3d.xaxis, self.ax_3d.yaxis, self.ax_3d.zaxis):
            axis.pane.set_facecolor(COR["card"])
            axis.pane.set_edgecolor(COR["borda"])
            axis.pane.set_alpha(0.55)
            axis._axinfo["grid"]["color"] = COR["borda"]
            axis._axinfo["grid"]["linewidth"] = 0.5

    def _desenha_3d_preview(self, code: str):
        try:
            w3d = self._le_wing_3d()
            x, y = engine.nacaGenerator(code, n_points=120)
            Xg, Yg, Zg = pipeline.build_wing_preview_mesh(x, y, w3d, n_sections=14, n_profile_pts=60)

            self.ax_3d.clear()
            self.fig_3d.patch.set_facecolor(COR["bg"])
            self.ax_3d.set_facecolor(COR["bg"])
            self._estiliza_eixo_3d()

            # Plota asa com envergadura no eixo Y visual e espessura no Z visual para melhor leitura 3D
            self.ax_3d.plot_surface(
                Xg, Zg, Yg,
                color=COR["azul"], alpha=0.88, edgecolor="#0F2A3F", linewidth=0.25, antialiased=True
            )
            self.ax_3d.set_xlabel("Corda X (mm)", color=COR["texto_sec"], fontsize=8, labelpad=4)
            self.ax_3d.set_ylabel("Envergadura Z (mm)", color=COR["texto_sec"], fontsize=8, labelpad=4)
            self.ax_3d.set_zlabel("Diedro / Esp. Y (mm)", color=COR["texto_sec"], fontsize=8, labelpad=4)
            self.ax_3d.tick_params(colors=COR["texto_dim"], labelsize=7, pad=1)
            self.ax_3d.set_title(
                f"Asa 3D — NACA {code}  |  b={w3d.span_mm:.0f} mm · c={w3d.root_chord_mm:.0f}→{w3d.tip_chord_mm:.0f} mm",
                color=COR["texto"], fontsize=9, pad=4
            )

            max_range = max(Xg.max() - Xg.min(), Zg.max() - Zg.min(), 1.0) / 2.0
            mid_x = (Xg.max() + Xg.min()) / 2.0
            mid_z = (Zg.max() + Zg.min()) / 2.0
            mid_y = (Yg.max() + Yg.min()) / 2.0
            self.ax_3d.set_xlim(mid_x - max_range, mid_x + max_range)
            self.ax_3d.set_ylim(mid_z - max_range, mid_z + max_range)
            self.ax_3d.set_zlim(mid_y - max_range * 0.4, mid_y + max_range * 0.4)
            self.ax_3d.view_init(elev=26, azim=-48)
            self.fig_3d.subplots_adjust(left=0.0, right=0.95, bottom=0.0, top=0.93)
            self.canvas_3d.draw_idle()
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
        target_path = Path(caminho)
        if tipo == "svg":
            saved = engine.export_svg(x, y, code, target_path)
        elif tipo == "dat":
            saved = engine.export_dat(x, y, code, target_path)
        else:
            saved = engine.export_json(code, res, self.cond_atual, Path(f"naca_{code}.dat"), target_path, extra_cfg=self.cfg_atual)
        messagebox.showinfo("Exportado!", f"NACA {code} salvo em:\n{saved}")

    def _gerar_3d_selecionada(self):
        if not self.top4 or self.cond_atual is None:
            messagebox.showwarning("Sem asa selecionada", "Execute a otimização e selecione uma das 4 asas primeiro.")
            return
        self._executar_pipeline_3d(self.selected_idx, self._le_wing_3d())

    def _executar_pipeline_3d(self, idx: int, w3d: pipeline.Wing3DParams):
        if self.gerando_3d or self.analisando:
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
        self._resetando = True
        try:
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
        finally:
            self._resetando = False

        self._atualiza_dados()
        code = self.top4[self.selected_idx][0] if self.top4 else "2412"
        self._desenha_3d_preview(code)
        self.lbl_status.config(text="Padrões restaurados.")

    def _ao_fechar(self):
        if self.analisando or self.gerando_3d:
            if not messagebox.askyesno("Processo em andamento", "Uma etapa da pipeline está em execução. Deseja fechar?"):
                return
        plt.close("all")
        self.root.destroy()


def main():
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    root = tk.Tk()
    WingLabsGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
