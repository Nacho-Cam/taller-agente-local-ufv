import contextlib
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from herramientas import conectar_claude

try:
    from mcp import Client
    from mcp.client.stdio import StdioServerParameters
    from integraciones.servidor_mcp import crear_servidor
    MCP_DISPONIBLE = True
except ModuleNotFoundError:
    MCP_DISPONIBLE = False


def datos(resultado):
    return json.loads(next(c.text for c in resultado.content if c.type == 'text'))


class ConfiguracionClaude(unittest.TestCase):
    def test_conserva_otros_servidores_y_es_idempotente(self):
        with tempfile.TemporaryDirectory() as temporal, patch.object(conectar_claude.shutil, 'which', return_value='uv'):
            raiz = Path(temporal)
            archivo = raiz / '.mcp.json'
            archivo.write_text(json.dumps({'mcpServers': {'otro': {'command': 'existente'}}}))
            conectar_claude.configurar(raiz)
            contenido = archivo.read_text(encoding='utf-8')
            conectar_claude.configurar(raiz)
            self.assertEqual(contenido, archivo.read_text(encoding='utf-8'))
            self.assertEqual(json.loads(contenido)['mcpServers']['otro']['command'], 'existente')
            self.assertTrue((raiz / '.claude/agents/tutor-ufv.md').is_file())

    def test_conflicto_no_modifica_configuracion_ni_agente(self):
        with tempfile.TemporaryDirectory() as temporal, patch.object(conectar_claude.shutil, 'which', return_value='uv'):
            raiz = Path(temporal)
            archivo = raiz / '.mcp.json'
            archivo.write_text('{"mcpServers": {"otro": {"command": "existente"}}}')
            agente = raiz / '.claude/agents/tutor-ufv.md'
            agente.parent.mkdir(parents=True)
            agente.write_text('Tutor personalizado', encoding='utf-8')
            antes = archivo.read_bytes()
            with self.assertRaises(ValueError):
                conectar_claude.configurar(raiz)
            self.assertEqual(archivo.read_bytes(), antes)
            self.assertEqual(agente.read_text(encoding='utf-8'), 'Tutor personalizado')


@unittest.skipUnless(MCP_DISPONIBLE, 'Instala el extra mcp para verificar la conexión.')
class ProtocoloMCP(unittest.IsolatedAsyncioTestCase):
    async def test_stdio_moderno_y_legacy_sin_ollama(self):
        raiz = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temporal:
            boveda = Path(temporal) / 'boveda'
            shutil.copytree(raiz / 'boveda/apuntes', boveda / 'apuntes')
            parametros = StdioServerParameters(command=sys.executable,
                args=[str(raiz / 'integraciones/servidor_mcp.py'), '--boveda', str(boveda)])
            for modo in ('auto', 'legacy'):
                async with Client(parametros, mode=modo, read_timeout_seconds=15) as cliente:
                    lista = await cliente.list_tools()
                    self.assertEqual({t.name for t in lista.tools},
                        {'buscar_apuntes', 'calcular_oee', 'consultar_tutor_local'})
                    encontrados = datos(await cliente.call_tool('buscar_apuntes', {'consulta': 'MQTT maqueta'}))
                    self.assertIn('taller/linea-roble/temperatura', json.dumps(encontrados))
                    calculo = await cliente.call_tool('calcular_oee', dict(
                        minutos_planificados=420, minutos_marcha=360, piezas_totales=600,
                        piezas_buenas=570, ciclo_ideal_segundos=30))
                    self.assertEqual(datos(calculo)['oee_pct'], 67.8571)
                    invalido = await cliente.call_tool('calcular_oee', dict(
                        minutos_planificados=True, minutos_marcha=1, piezas_totales=1,
                        piezas_buenas=1, ciclo_ideal_segundos=1))
                    self.assertTrue(invalido.is_error)
                    error = await cliente.call_tool('guardar_memoria', {'titulo': 'No guardar'})
                    self.assertTrue(error.is_error)
            self.assertFalse((boveda / 'memoria').exists())

    async def test_delegacion_no_puede_guardar_y_no_escribe_en_stdout(self):
        with tempfile.TemporaryDirectory() as temporal:
            raiz = Path(temporal)
            servidor = crear_servidor(raiz)

            def agente_simulado(mensajes, modelo, boveda, **opciones):
                nombres = [h['function']['name'] for h in opciones['herramientas']]
                self.assertNotIn('guardar_memoria', nombres)
                with self.assertRaises(ValueError):
                    opciones['ejecutar']('guardar_memoria', {'titulo': 'No guardar'}, boveda)
                opciones['informar']('Traza de prueba')
                return 'Respuesta simulada, no inferencia real.'

            salida = io.StringIO()
            with patch('integraciones.servidor_mcp.resolver_turno', side_effect=agente_simulado):
                async with Client(servidor, read_timeout_seconds=15) as cliente:
                    with contextlib.redirect_stdout(salida):
                        resultado = await cliente.call_tool('consultar_tutor_local', {'pregunta': 'Repasar OEE'})
            self.assertFalse(resultado.is_error)
            self.assertFalse(datos(resultado)['escritura_permitida'])
            self.assertEqual(salida.getvalue(), '')
            self.assertFalse((raiz / 'memoria').exists())
