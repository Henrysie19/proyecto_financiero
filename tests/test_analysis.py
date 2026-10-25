import unittest

from src.analysis import build_strategy_analysis


class BuildStrategyAnalysisTests(unittest.TestCase):
    def test_describes_oversold_without_promising_rebound(self):
        category, title, explanation = build_strategy_analysis("SPY", 90, 100, -2.5, 2)

        self.assertEqual(category, "oversold")
        self.assertIn("Posible sobreventa", title)
        self.assertIn("no confirma una oportunidad", explanation)
        self.assertIn("no recomendación personalizada", explanation)

    def test_describes_overbought_without_predicting_drop(self):
        category, title, explanation = build_strategy_analysis("SPY", 110, 100, 2.5, 2)

        self.assertEqual(category, "overbought")
        self.assertIn("Posible sobrecompra", title)
        self.assertIn("no predice una corrección", explanation)

    def test_describes_neutral_state(self):
        category, title, explanation = build_strategy_analysis("SPY", 101, 100, 1.2, 2)

        self.assertEqual(category, "neutral")
        self.assertEqual(title, "Rango estadístico neutral")
        self.assertIn("no muestra una desviación extrema", explanation)

    def test_handles_missing_z_score(self):
        category, title, explanation = build_strategy_analysis("SPY", 100, None, None, 2)

        self.assertEqual(category, "warning")
        self.assertEqual(title, "Análisis no disponible todavía")
        self.assertIn("completar la ventana", explanation)

    def test_rejects_invalid_threshold(self):
        with self.assertRaises(ValueError):
            build_strategy_analysis("SPY", 100, 100, 0, 0)


if __name__ == "__main__":
    unittest.main()
