import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from herramientas import conectar_gemini as gemini

try:
    from mcp import Client
    from mcp.client.stdio import StdioServerParameters
    MCP_DISPONIBLE = True
except ModuleNotFoundError:
    MCP_DISPONIBLE = False


class ConfiguracionGemini(unittest.TestCase):
    def test_preserva_bom_otros_valores_y_respaldo_idempotente(self):
        with tempfile.TemporaryDirectory() as temporal:
            raiz = Path(temporal)
            archivo = raiz / '.gemini/settings.json'
            archivo.parent.mkdir()
            original = b'\xef\xbb\xbf{"theme":"oscuro","mcpServers":{"otro":{"command":"existente"}}}'
            archivo.write_bytes(original)
            rutas = gemini.configurar(raiz)
            primero = archivo.read_bytes()
            gemini.configurar(raiz)
            self.assertEqual(archivo.read_bytes(), primero)
            self.assertEqual(archivo.with_name('settings.json.ufv-backup').read_bytes(), original)
            config = json.loads(primero)
            self.assertEqual(config['theme'], 'oscuro')
            self.assertEqual(config['mcpServers']['otro'], {'command': 'existente'})
            entrada = config['mcpServers']['ufv-local']
            self.assertFalse(entrada['trust'])
            self.assertEqual(entrada['timeout'], 180000)
            self.assertNotIn('consultar_tutor_local', entrada['includeTools'])
            self.assertEqual(set(entrada['includeTools']), {'buscar_apuntes', 'calcular_oee', *gemini.NOMBRES})
            self.assertTrue(all(ruta.exists() for ruta in rutas))

    def test_modelo_local_es_optativo(self):
        with tempfile.TemporaryDirectory() as temporal:
            archivo, _ = gemini.configurar(temporal, modelo_local=True)
            entrada = json.loads(archivo.read_text())['mcpServers']['ufv-local']
            self.assertIn('consultar_tutor_local', entrada['includeTools'])

    def test_gemini_personalizado_no_toca_settings(self):
        with tempfile.TemporaryDirectory() as temporal:
            raiz = Path(temporal)
            instrucciones = raiz / 'GEMINI.md'
            instrucciones.write_text('Mis instrucciones')
            with self.assertRaisesRegex(ValueError, 'personalizado'):
                gemini.configurar(raiz)
            self.assertFalse((raiz / '.gemini').exists())
            self.assertEqual(instrucciones.read_text(), 'Mis instrucciones')

    def test_conflicto_servidor_no_escribe_instrucciones_ni_respaldo(self):
        with tempfile.TemporaryDirectory() as temporal:
            raiz = Path(temporal)
            archivo = raiz / '.gemini/settings.json'
            archivo.parent.mkdir()
            original = b'{"mcpServers":{"ufv-local":{"command":"otro"}}}'
            archivo.write_bytes(original)
            with self.assertRaisesRegex(ValueError, 'otro servidor'):
                gemini.configurar(raiz)
            self.assertEqual(archivo.read_bytes(), original)
            self.assertFalse((raiz / 'GEMINI.md').exists())
            self.assertFalse(archivo.with_name('settings.json.ufv-backup').exists())

    def test_rechaza_json_invalido_y_mcp_servers_no_objeto(self):
        for contenido in ('[]', '{"mcpServers": []}', '{'):
            with self.subTest(contenido=contenido), tempfile.TemporaryDirectory() as temporal:
                raiz = Path(temporal)
                archivo = raiz / '.gemini/settings.json'
                archivo.parent.mkdir()
                archivo.write_text(contenido)
                with self.assertRaises(ValueError):
                    gemini.configurar(raiz)
                self.assertEqual(archivo.read_text(), contenido)
                self.assertFalse((raiz / 'GEMINI.md').exists())

    def test_rechaza_junction_o_enlace_directorio(self):
        with tempfile.TemporaryDirectory() as temporal:
            raiz = Path(temporal)
            proyecto, externo = raiz / 'proyecto', raiz / 'externo'
            proyecto.mkdir()
            externo.mkdir()
            enlace = proyecto / '.gemini'
            if os.name == 'nt':
                resultado = subprocess.run(['cmd', '/c', 'mklink', '/J', str(enlace), str(externo)], capture_output=True)
                self.assertEqual(resultado.returncode, 0)
            else:
                enlace.symlink_to(externo, target_is_directory=True)
            try:
                with self.assertRaisesRegex(ValueError, 'enlace o junction'):
                    gemini.configurar(proyecto)
                self.assertEqual(list(externo.iterdir()), [])
            finally:
                enlace.rmdir() if os.name == 'nt' else enlace.unlink()

    def test_rechaza_enlaces_archivos_y_respaldo(self):
        with tempfile.TemporaryDirectory() as temporal:
            raiz = Path(temporal)
            externo = raiz / 'externo.txt'
            externo.write_text('Intacto')
            for nombre in ('GEMINI.md', '.gemini/settings.json', '.gemini/settings.json.ufv-backup'):
                ruta = raiz / nombre
                ruta.parent.mkdir(exist_ok=True)
                try:
                    ruta.symlink_to(externo)
                except OSError:
                    self.skipTest('Crear symlinks requiere permisos en este Windows.')
                try:
                    with self.assertRaisesRegex(ValueError, 'enlace o junction'):
                        gemini.configurar(raiz)
                    self.assertEqual(externo.read_text(), 'Intacto')
                finally:
                    ruta.unlink()


@unittest.skipUnless(MCP_DISPONIBLE, 'Instala el extra mcp para probar STDIO.')
class GeminiMCP(unittest.IsolatedAsyncioTestCase):
    async def test_configuracion_generada_opera_carrera_sin_ollama(self):
        with tempfile.TemporaryDirectory() as temporal:
            raiz = Path(temporal)
            boveda = raiz / 'boveda'
            boveda.mkdir()
            archivo, _ = gemini.configurar(raiz, boveda)
            entrada = json.loads(archivo.read_text())['mcpServers']['ufv-local']
            # Ejecuta exactamente el comando uv generado: no sustituye el servidor.
            parametros = StdioServerParameters(command=entrada['command'], args=entrada['args'])
            async with Client(parametros, read_timeout_seconds=60) as cliente:
                catalogo = {tool.name for tool in (await cliente.list_tools()).tools}
                self.assertTrue(set(entrada['includeTools']).issubset(catalogo))
                for nombre, argumentos in (
                    ('crear_curso', {'nombre': 'Tercero'}),
                    ('crear_asignatura', {'curso': 'Tercero', 'nombre': 'Control'}),
                    ('anadir_material', {'curso': 'Tercero', 'asignatura': 'Control', 'tipo': 'apunte',
                                        'titulo': 'Sensores', 'tema': 'Medicion', 'contenido': 'El sensor P101 usa MQTT.'}),
                    ('buscar_apuntes', {'consulta': 'P101 MQTT', 'curso': 'Tercero', 'asignatura': 'Control'}),
                ):
                    resultado = await cliente.call_tool(nombre, argumentos)
                    self.assertFalse(resultado.is_error, resultado)
                texto = '\n'.join(c.text for c in resultado.content if c.type == 'text')
                self.assertIn('P101', texto)
