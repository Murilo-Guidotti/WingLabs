from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from winglabs.aero import naca_tester as NacaTester
from winglabs.aero import optimizer
from winglabs.aero import xfoil_engine
from winglabs.core import environment as env
from winglabs.core import naca as ng
from winglabs.core import pipeline


class TestWingLabsCore(unittest.TestCase):
    def test_naca_generator_symmetric_0012(self):
        x, y = ng.generator("0012", 101)
        self.assertEqual(len(x), 201)
        self.assertEqual(len(y), 201)
        # Perfil simétrico: média de y próxima de zero e extremos em [0, 1]
        self.assertAlmostEqual(float(np.min(x)), 0.0, places=5)
        self.assertAlmostEqual(float(np.max(x)), 1.0, places=5)
        self.assertAlmostEqual(float(np.mean(y)), 0.0, places=4)
        # Espessura máxima ~12% da corda (y_max - y_min ≈ 0.12)
        thickness = float(np.max(y) - np.min(y))
        self.assertAlmostEqual(thickness, 0.12, delta=0.005)

    def test_naca_generator_cambered_2412(self):
        x, y = ng.generator("2412", 120)
        self.assertEqual(len(x), 239)
        self.assertGreater(float(np.max(y)), abs(float(np.min(y))))

    def test_isa_and_flight_conditions(self):
        cond = env.FlightConditions(altitude=1500.0, velocity=60.0, target_cl=0.8, chord_size=1.2)
        self.assertGreater(cond.rho, 0.9)
        self.assertLess(cond.rho, 1.25)
        self.assertGreater(cond.reynolds, 3_000_000)
        self.assertGreater(cond.mach, 0.1)
        self.assertLess(cond.mach, 0.3)

    def test_wing_area_and_required_cl(self):
        area = env.wing_area_m2(5000.0, 1200.0, 700.0)
        self.assertAlmostEqual(area, 4.75, places=4)
        cl_req = env.required_cl(payload_kg=120.0, rho=1.0581, velocity=60.0, area_m2=area)
        self.assertAlmostEqual(cl_req, 0.1301, places=3)
        with self.assertRaises(ValueError):
            env.required_cl(120.0, 0.0, 60.0, area)

    def test_select_best_polar_point_payload_and_target_cl(self):
        cond = env.FlightConditions(altitude=1500.0, velocity=60.0, target_cl=0.5, chord_size=1.2)
        polar = [
            {"alpha": 0.0, "cl": 0.25, "cd": 0.0070, "cm": -0.05},
            {"alpha": 3.0, "cl": 0.52, "cd": 0.0065, "cm": -0.05},
            {"alpha": 6.0, "cl": 0.85, "cd": 0.0150, "cm": -0.06},
        ]
        # Modo payload com required_cl = 0.40 e área 4.75 m²
        best_payload = xfoil_engine.select_best_polar_point(
            polar, cond, {"search_mode": "payload", "required_cl": 0.40, "wing_area_m2": 4.75}
        )
        self.assertIsNotNone(best_payload)
        self.assertEqual(best_payload["alpha_opt"], 3.0)
        self.assertIn("lift_kg", best_payload)

        # Modo target_cl com tolerância 0.05 em torno de 0.5
        best_cl = xfoil_engine.select_best_polar_point(
            polar, cond, {"search_mode": "target_cl", "cl_tolerance": 0.05}
        )
        self.assertIsNotNone(best_cl)
        self.assertEqual(best_cl["alpha_opt"], 3.0)

    def test_valida_resultado_handles_none_defaults(self):
        cond = env.FlightConditions(altitude=1500.0, velocity=60.0, target_cl=0.8, chord_size=1.2)
        res_ok = {"cl": 0.8, "cd": 0.0085, "efficiency": 94.1}
        # Mesmo se cd_min e eff_max não estiverem em cfg, não deve lançar TypeError
        self.assertTrue(NacaTester._valida_resultado(res_ok, {}, cond))
        res_unphysical = {"cl": 0.8, "cd": 0.0001, "efficiency": 8000.0}
        self.assertFalse(NacaTester._valida_resultado(res_unphysical, {}, cond))

    def test_exporters_respect_custom_file_path_and_directory(self):
        cond = env.FlightConditions(altitude=1500.0, velocity=60.0, target_cl=0.8, chord_size=1.2)
        res = {"alpha_opt": 4.5, "cl": 0.82, "cd": 0.0081, "cm": -0.09, "efficiency": 101.2, "lift_n": 1500.0, "lift_kg": 152.9}
        x, y = ng.generator("2412", 60)

        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            # Caminho personalizado (ex.: retornado por asksaveasfilename)
            custom_svg = tmp_dir / "minha_asa_custom.svg"
            custom_dat = tmp_dir / "minha_asa_custom.dat"
            custom_json = tmp_dir / "minha_asa_custom.json"
            custom_png = tmp_dir / "minha_asa_custom.png"

            self.assertEqual(xfoil_engine.export_svg(x, y, "2412", custom_svg), custom_svg)
            self.assertEqual(xfoil_engine.export_dat(x, y, "2412", custom_dat), custom_dat)
            self.assertEqual(xfoil_engine.export_json("2412", res, cond, custom_dat, custom_json), custom_json)
            self.assertEqual(xfoil_engine.export_plot(x, y, "2412", res, custom_png), custom_png)

            self.assertTrue(custom_svg.exists())
            self.assertTrue(custom_dat.exists())
            self.assertTrue(custom_json.exists())
            self.assertTrue(custom_png.exists())

            data = json.loads(custom_json.read_text(encoding="utf-8"))
            self.assertEqual(data["naca_code"], "2412")

    def test_build_wing_preview_mesh_vectorized(self):
        x, y = ng.generator("2412", 80)
        params = pipeline.Wing3DParams(span_mm=5000.0, root_chord_mm=1200.0, tip_chord_mm=700.0)
        Xg, Yg, Zg = pipeline.build_wing_preview_mesh(x, y, params, n_sections=14, n_profile_pts=60)
        self.assertEqual(Xg.shape, (15, 60))
        self.assertEqual(Yg.shape, (15, 60))
        self.assertEqual(Zg.shape, (15, 60))
        self.assertAlmostEqual(float(Zg.min()), 0.0, places=4)
        self.assertAlmostEqual(float(Zg.max()), 5000.0, places=4)

    def test_twist_pivots_around_quarter_chord_and_3d_config_fields(self):
        # Ponto exato no centro aerodinâmico (x=0.25, y=0.0) deve permanecer fixo sob torção
        x = np.array([0.0, 0.25, 1.0, 0.25])
        y = np.array([0.0, 0.0, 0.0, 0.0])
        p_no_twist = pipeline.Wing3DParams(
            span_mm=1000.0, root_chord_mm=400.0, tip_chord_mm=200.0, tip_twist_deg=0.0
        )
        p_twisted = pipeline.Wing3DParams(
            span_mm=1000.0, root_chord_mm=400.0, tip_chord_mm=200.0, tip_twist_deg=-15.0,
            shell_thickness_mm=3.5, export_voxel_mesh=True,
        )
        X0, Y0, _ = pipeline.build_wing_preview_mesh(x, y, p_no_twist, n_sections=4, n_profile_pts=4)
        Xt, Yt, _ = pipeline.build_wing_preview_mesh(x, y, p_twisted, n_sections=4, n_profile_pts=4)

        # Coluna 1 corresponde a (x=0.25, y=0.0): invariante com a torção em todas as seções
        np.testing.assert_allclose(X0[:, 1], Xt[:, 1], atol=1e-6)
        np.testing.assert_allclose(Y0[:, 1], Yt[:, 1], atol=1e-6)
        # Bordo de ataque (coluna 0, x=0.0) e bordo de fuga (coluna 2, x=1.0) deslocam em sentidos opostos em Y na ponta
        self.assertGreater(Yt[-1, 0], 0.0)
        self.assertLess(Yt[-1, 2], 0.0)

        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            cfg_path = pipeline.write_3d_config(
                tmp_dir / "naca_2412.dat",
                tmp_dir / "wing.stl",
                p_twisted,
                tmp_dir / "wing3d_config.json",
            )
            payload = json.loads(cfg_path.read_text(encoding="utf-8"))
            self.assertAlmostEqual(payload["shell_thickness_mm"], 3.5)
            self.assertTrue(payload["export_voxel_mesh"])
            self.assertTrue(payload["elliptical_transition"])

    def test_nonlinear_interpolation_and_elliptical_transition(self):
        x = np.array([0.0, 1.0])
        y = np.array([0.0, 0.0])
        p_lin = pipeline.Wing3DParams(
            span_mm=1000.0, root_chord_mm=400.0, tip_chord_mm=200.0,
            tip_twist_deg=0.0, wing_sweep_deg=0.0, elliptical_transition=False,
        )
        p_ellip = pipeline.Wing3DParams(
            span_mm=1000.0, root_chord_mm=400.0, tip_chord_mm=200.0,
            tip_twist_deg=0.0, wing_sweep_deg=0.0, elliptical_transition=True,
        )
        X_lin, _, Z_lin = pipeline.build_wing_preview_mesh(x, y, p_lin, n_sections=10, n_profile_pts=2)
        X_ell, _, Z_ell = pipeline.build_wing_preview_mesh(x, y, p_ellip, n_sections=10, n_profile_pts=2)

        # Agrupamento não-linear concentra estações mais perto da ponta (Z_ell > Z_lin nas estações intermediárias)
        self.assertGreater(float(Z_ell[5, 0]), float(Z_lin[5, 0]))

        # Corda na meia-envergadura na distribuição elíptica é maior que na linear trapezoidal
        chord_mid_lin = float(X_lin[5, 1] - X_lin[5, 0])
        chord_mid_ell = float(X_ell[5, 1] - X_ell[5, 0])
        self.assertGreater(chord_mid_ell, chord_mid_lin)

        # Na ponta (última seção), a transição elíptica truncada converge suavemente para c_tip sem quina
        chord_tip_ell = float(X_ell[-1, 1] - X_ell[-1, 0])
        self.assertAlmostEqual(chord_tip_ell, 200.0, places=4)

    def test_custom_sections_and_rounded_cylindrical_tip_cap(self):
        x, y = ng.generator("0012", 40)
        base_params = pipeline.Wing3DParams(
            span_mm=1000.0, root_chord_mm=300.0, tip_chord_mm=150.0,
            target_section_size_mm=250.0, rounded_tip_cap=True, tip_cap_radius_mm=50.0,
        )
        secs = pipeline.generate_wing_sections(base_params, n_sections=4)
        self.assertEqual(len(secs), 5)
        # Edita manualmente a seção intermediária #2
        secs[2].chord_mm = 420.0
        secs[2].twist_deg = -8.5
        secs[2].thickness_scale = 1.25
        base_params.custom_sections = secs

        Xg, Yg, Zg = pipeline.build_wing_preview_mesh(x, y, base_params, n_sections=4, n_profile_pts=30)
        # 5 seções customizadas + 6 anéis da ponta cilíndrica/elíptica = 11 estações
        self.assertEqual(Xg.shape, (11, 30))
        # Envergadura total se estende de 0 até span_mm + tip_cap_radius_mm (1000 + 50 = 1050 mm)
        self.assertAlmostEqual(float(Zg.min()), 0.0, places=3)
        self.assertAlmostEqual(float(Zg.max()), 1050.0, places=3)
        # No último anel da ponta cilíndrica (Zg = 1050 mm), a espessura Y converge para ~0 (fechamento curvo)
        tip_y_span = float(Yg[-1, :].max() - Yg[-1, :].min())
        root_y_span = float(Yg[0, :].max() - Yg[0, :].min())
        self.assertLess(tip_y_span, root_y_span * 0.05)

        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            cfg_path = pipeline.write_3d_config(
                tmp_dir / "naca_0012.dat",
                tmp_dir / "wing.stl",
                base_params,
                tmp_dir / "wing3d_config.json",
            )
            payload = json.loads(cfg_path.read_text(encoding="utf-8"))
            self.assertTrue(payload["rounded_tip_cap"])
            self.assertAlmostEqual(payload["tip_cap_radius_mm"], 50.0)
            self.assertEqual(len(payload["custom_sections"]), 5)
            self.assertAlmostEqual(payload["custom_sections"][2]["chord_mm"], 420.0)
            self.assertAlmostEqual(payload["custom_sections"][2]["thickness_scale"], 1.25)

    def test_two_stage_optimizer_coarse_to_fine(self):
        from unittest import mock

        cond = env.FlightConditions(altitude=1500.0, velocity=60.0, target_cl=0.8, chord_size=1.2)
        cfg = {
            "search_mode": "target_cl",
            "cl_tolerance": 0.15,
            "camber_max": 2,          # 3 (M=0..2) * 6 (P=2..7) * 2 (T=10,12) = 36 perfis (> 8 -> 2 estágios)
            "espessuras": [10, 12],
            "n_panels": 240,
            "n_ITER": 100,
            "alpha_start": -2.0,
            "alpha_end": 10.0,
            "alpha_step": 0.5,
            "n_threads": 2,
        }

        calls_by_panels: list[int] = []

        def _fake_tester_run(args):
            code, _cond, stage_cfg, _idx, _total = args
            calls_by_panels.append(int(stage_cfg["n_panels"]))
            eff = 80.0 + int(code[0]) * 10.0 + int(code[1])
            return code, {
                "alpha_opt": 3.0,
                "cl": 0.80,
                "cd": 0.0080,
                "cm": -0.05,
                "efficiency": eff,
            }

        with mock.patch("winglabs.aero.naca_tester.run", side_effect=_fake_tester_run):
            best_code, best_res, top4 = optimizer.run(cond, cfg)

        self.assertIsNotNone(best_res)
        self.assertEqual(len(top4), 4)
        # Estágio 1 roda todos os 36 perfis com 120 painéis; Estágio 2 roda apenas o Top 15% (6 perfis) com 240 painéis
        coarse_calls = [p for p in calls_by_panels if p == 120]
        fine_calls = [p for p in calls_by_panels if p == 240]
        self.assertEqual(len(coarse_calls), 36)
        self.assertEqual(len(fine_calls), 6)
        self.assertEqual(best_code, top4[0][0])


class TestWingLabsUILayout(unittest.TestCase):
    def setUp(self):
        import tkinter as tk
        from winglabs.ui import app as interface

        self.tk = tk
        self.interface = interface
        self.root = tk.Tk()
        self.gui = interface.WingLabsGUI(self.root)
        self.root.update_idletasks()
        self.root.update()

    def tearDown(self):
        import matplotlib.pyplot as plt

        if self.gui._debounce_3d_id is not None:
            try:
                self.root.after_cancel(self.gui._debounce_3d_id)
            except Exception:
                pass
        plt.close("all")
        try:
            self.root.destroy()
        except Exception:
            pass

    def test_zero_spacing_between_main_panels(self):
        """Valida que body, sidebar e workspace não possuem espaçamentos externos ou entre si."""
        body_pack = self.gui.body.pack_info()
        sb_pack = self.gui.sidebar.pack_info()
        ws_pack = self.gui.workspace.pack_info()

        self.assertEqual(int(body_pack["padx"]), 0)
        self.assertEqual(int(body_pack["pady"]), 0)
        self.assertEqual(int(sb_pack["padx"]), 0)
        self.assertEqual(int(sb_pack["pady"]), 0)
        self.assertEqual(int(ws_pack["padx"]), 0)
        self.assertEqual(int(ws_pack["pady"]), 0)

        gap_sb_ws = self.gui.workspace.winfo_x() - (self.gui.sidebar.winfo_x() + self.gui.sidebar.winfo_width())
        self.assertEqual(gap_sb_ws, 0, f"Esperado gap 0px entre sidebar e workspace, obtido {gap_sb_ws}px")

    def test_zero_spacing_between_workspace_windows_vertical_and_horizontal(self):
        """Valida 0px de espaçamento entre Top 4 cards, janelas 2D/3D e barra inferior de KPIs."""
        # Adjacência vertical: top_hdr -> cards_frame -> view_frame -> bottom_panel
        gap_hdr_cards = self.gui.cards_frame.winfo_y() - (self.gui.top_hdr.winfo_y() + self.gui.top_hdr.winfo_height())
        gap_cards_view = self.gui.view_frame.winfo_y() - (self.gui.cards_frame.winfo_y() + self.gui.cards_frame.winfo_height())
        gap_view_bottom = self.gui.bottom_panel.winfo_y() - (self.gui.view_frame.winfo_y() + self.gui.view_frame.winfo_height())

        self.assertEqual(gap_hdr_cards, 0)
        self.assertEqual(gap_cards_view, 0)
        self.assertEqual(gap_view_bottom, 0)

        # Adjacência horizontal dos 4 cards do Top 4
        for i in range(4):
            g_info = self.gui.top4_widgets[i]["card"].grid_info()
            self.assertEqual(int(g_info["padx"]), 0)
            self.assertEqual(int(g_info["pady"]), 0)
        for i in range(3):
            c_curr = self.gui.top4_widgets[i]["card"]
            c_next = self.gui.top4_widgets[i + 1]["card"]
            gap_card = c_next.winfo_x() - (c_curr.winfo_x() + c_curr.winfo_width())
            self.assertEqual(gap_card, 0, f"Gap entre card #{i+1} e #{i+2}: {gap_card}px")

        # Adjacência horizontal entre janela 2D (p2d) e janela 3D (p3d)
        gap_2d_3d = self.gui.p3d.winfo_x() - (self.gui.p2d.winfo_x() + self.gui.p2d.winfo_width())
        self.assertEqual(gap_2d_3d, 0, f"Esperado 0px entre p2d e p3d, obtido {gap_2d_3d}px")
        self.assertEqual(self.gui.p2d.winfo_height(), self.gui.p3d.winfo_height())

        # Adjacência horizontal entre os 6 cards de KPI inferiores
        for i in range(len(self.gui.kpi_boxes) - 1):
            b_curr = self.gui.kpi_boxes[i]
            b_next = self.gui.kpi_boxes[i + 1]
            gap_kpi = b_next.winfo_x() - (b_curr.winfo_x() + b_curr.winfo_width())
            self.assertEqual(gap_kpi, 0, f"Gap entre KPI {i} e {i+1}: {gap_kpi}px")

    def test_2d_and_3d_canvases_full_bleed_and_selection_flow(self):
        """Valida que os canvases 2D e 3D ocupam 100% da área interna sem margens mortas e atualizam ao selecionar."""
        w2d_pack = self.gui.w2d.pack_info()
        w3d_pack = self.gui.w3d.pack_info()
        self.assertEqual(int(w2d_pack["padx"]), 0)
        self.assertEqual(int(w2d_pack["pady"]), 0)
        self.assertEqual(int(w3d_pack["padx"]), 0)
        self.assertEqual(int(w3d_pack["pady"]), 0)

        self.assertEqual(self.gui.fig_2d.get_facecolor(), self.gui.ax_2d.get_facecolor())
        self.assertEqual(self.gui.fig_3d.get_facecolor(), self.gui.ax_3d.get_facecolor())

        # Simula 4 candidatos e valida troca de seleção em tempo real
        self.gui.top4 = [
            ("4412", {"cl": 0.82, "cd": 0.0075, "cm": -0.09, "efficiency": 109.3, "alpha_opt": 4.0, "lift_kg": 155.0}),
            ("2412", {"cl": 0.68, "cd": 0.0068, "cm": -0.05, "efficiency": 100.0, "alpha_opt": 3.5, "lift_kg": 132.0}),
            ("2315", {"cl": 0.61, "cd": 0.0065, "cm": -0.04, "efficiency": 93.8, "alpha_opt": 3.0, "lift_kg": 121.0}),
            ("0012", {"cl": 0.50, "cd": 0.0062, "cm": 0.00, "efficiency": 80.6, "alpha_opt": 4.5, "lift_kg": 98.0}),
        ]
        self.gui._atualiza_cards_top4()
        self.gui._selecionar_asa(0)
        self.root.update_idletasks()
        self.assertEqual(self.gui.kpi_labels["code"].cget("text"), "NACA 4412")
        self.assertEqual(self.gui.top4_widgets[0]["tag"].cget("text"), "SELECIONADA")

        self.gui._selecionar_asa(2)
        self.root.update_idletasks()
        self.assertEqual(self.gui.kpi_labels["code"].cget("text"), "NACA 2315")
        self.assertEqual(self.gui.top4_widgets[2]["tag"].cget("text"), "SELECIONADA")
        self.assertEqual(self.gui.top4_widgets[0]["tag"].cget("text"), "")

        # Valida seções recolhíveis (Geometria 3D, Editor por Seção e Busca & XFOIL)
        self.assertFalse(self.gui.geometria_3d_aberta)
        self.assertEqual(self.gui.body_3d.winfo_manager(), "")
        self.gui._toggle_geometria_3d()
        self.assertTrue(self.gui.geometria_3d_aberta)
        self.assertEqual(self.gui.body_3d.winfo_manager(), "pack")
        self.gui._toggle_geometria_3d()
        self.assertFalse(self.gui.geometria_3d_aberta)
        self.assertEqual(self.gui.body_3d.winfo_manager(), "")

        self.assertFalse(self.gui.secoes_3d_aberto)
        self.assertEqual(self.gui.body_secoes.winfo_manager(), "")
        self.gui._toggle_secoes_3d()
        self.assertTrue(self.gui.secoes_3d_aberto)
        self.assertEqual(self.gui.body_secoes.winfo_manager(), "pack")
        self.gui._toggle_secoes_3d()
        self.assertFalse(self.gui.secoes_3d_aberto)
        self.assertEqual(self.gui.body_secoes.winfo_manager(), "")


if __name__ == "__main__":
    unittest.main()
