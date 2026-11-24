import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import nucleo
from solucion import agente


class PruebasTaller(unittest.TestCase):
    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)
        self.boveda = Path(self.temporal.name)
        (self.boveda / "apuntes").mkdir()
        (self.boveda / "apuntes" / "Maqueta.md").write_text(
            "# Maqueta\n\nEl sensor Faro-27 mide presión cada 7 segundos.\n", encoding="utf-8")

    def test_busca_acentos_y_no_inventa_resultados(self):
        resultado = nucleo.buscar_apuntes("PRESION Faro", self.boveda)
        self.assertEqual(resultado["resultados"][0]["fuente"], "apuntes/Maqueta.md")
        self.assertIn("7 segundos", resultado["resultados"][0]["texto"])
        self.assertEqual(nucleo.buscar_apuntes("zebras", self.boveda)["resultados"], [])

    def test_rechazar_memoria_no_escribe(self):
        resultado = nucleo.guardar_memoria("Objetivo", "Repasar OEE", self.boveda, confirmar=lambda _: "n")
        self.assertFalse(resultado["guardado"])
        self.assertFalse((self.boveda / "memoria").exists())

    def test_memoria_sobrevive_al_reinicio_y_se_recarga(self):
        guardado = nucleo.guardar_memoria("Objetivo", "Repasar OEE", self.boveda, confirmar=lambda _: "s")
        self.assertTrue(guardado["guardado"])
        mensajes = nucleo.nuevos_mensajes(self.boveda)
        self.assertIn("Repasar OEE", mensajes[1]["content"])
        archivo = self.boveda / guardado["archivo"]
        archivo.write_text("# Nuevo objetivo\nRepasar sensores", encoding="utf-8")
        self.assertIn("Repasar sensores", nucleo.nuevos_mensajes(self.boveda)[1]["content"])
        self.assertTrue(nucleo.buscar_apuntes("sensores", self.boveda)["resultados"])

    def test_oee_unidades_y_datos_inconsistentes(self):
        resultado = nucleo.calcular_oee(420, 360, 600, 570, 30)
        self.assertAlmostEqual(resultado["oee_pct"], 67.8571)
        for valores in ((420, 0, 600, 570, 30), (420, 360, 600, 650, 30),
                        (420, 360, 600, 570, float("inf")), (420, 360, 600.5, 570, 30)):
            with self.assertRaises(ValueError):
                nucleo.calcular_oee(*valores)

    def test_herramientas_solo_permiten_funciones_conocidas(self):
        with self.assertRaises(ValueError):
            nucleo.ejecutar_herramienta("ejecutar_shell", {"cmd": "algo"}, self.boveda)
        with self.assertRaises(TypeError):
            nucleo.ejecutar_herramienta("buscar_apuntes", {"consulta": "Faro", "ruta": "otro"}, self.boveda)

    def test_ciclo_real_del_programa_con_respuesta_modelo_simulada(self):
        mensajes = nucleo.nuevos_mensajes(self.boveda) + [{"role": "user", "content": "Busca Faro"}]
        respuestas = [
            {"role": "assistant", "content": "", "tool_calls": [
                {"function": {"name": "buscar_apuntes", "arguments": {"consulta": "Faro"}}}]},
            {"role": "assistant", "content": "Cada 7 segundos [apuntes/Maqueta.md:1-3]."},
        ]
        with patch.object(agente, "chat", side_effect=respuestas):
            respuesta = agente.resolver_turno(mensajes, "simulado", self.boveda)
        self.assertIn("7 segundos", respuesta)
        self.assertEqual(mensajes[-2]["role"], "tool")
        self.assertEqual(mensajes[-2]["tool_name"], "buscar_apuntes")
        self.assertIn("Faro-27", json.loads(mensajes[-2]["content"])["resultados"][0]["texto"])

    def test_error_herramienta_se_devuelve_al_modelo(self):
        respuestas = [
            {"role": "assistant", "tool_calls": [{"function": {"name": "desconocida", "arguments": {}}}]},
            {"role": "assistant", "content": "No puedo ejecutar esa herramienta."},
        ]
        mensajes = []
        with patch.object(agente, "chat", side_effect=respuestas):
            agente.resolver_turno(mensajes, "simulado", self.boveda)
        self.assertIn("desconocida", json.loads(mensajes[1]["content"])["error"])

    def test_bucle_tiene_limite(self):
        repetida = {"role": "assistant", "tool_calls": [{"function": {
            "name": "buscar_apuntes", "arguments": {"consulta": "Faro"}}}]}
        with patch.object(agente, "chat", return_value=repetida) as llamada:
            with self.assertRaisesRegex(RuntimeError, "agotó"):
                agente.resolver_turno([], "simulado", self.boveda)
        self.assertEqual(llamada.call_count, nucleo.MAX_RONDAS)


if __name__ == "__main__":
    unittest.main()
