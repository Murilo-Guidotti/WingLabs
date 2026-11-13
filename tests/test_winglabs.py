from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from winglabs.aero import naca_tester as NacaTester
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


if __name__ == "__main__":
    unittest.main()
