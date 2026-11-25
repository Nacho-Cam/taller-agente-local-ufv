import concurrent.futures
import json
import tempfile
import threading
import time
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import entorno_local
import nucleo
from herramientas import entorno


def hardware(tipo='nvidia', vram=8192, libre=7600, ram=16, disponible=10):
    gpu = {'tipo': tipo, 'nombre': 'GPU de prueba', 'vram_mb': vram, 'libre_mb': libre, 'indice': 0}
    return {'sistema': 'Windows', 'arquitectura': 'amd64', 'ram_gb': ram, 'ram_disponible_gb': disponible,
            'cpu_hilos': 8, 'gpu': [gpu] if tipo else []}


class Perfiles(unittest.TestCase):
    def test_opencode_abre_materiales_y_mcp_preconfigurados_sin_cambiar_readme(self):
        with tempfile.TemporaryDirectory() as t:
            raiz = Path(t)
            (raiz / 'README.md').write_text('Mi documentación', encoding='utf-8')
            config = entorno_local.perfil(hardware())
            with patch.object(entorno, 'RAIZ', raiz), patch.object(entorno, 'LOCAL', raiz / '.local'):
                self.assertEqual(entorno.configurar_opencode(config), raiz)
            datos = json.loads((raiz / 'opencode.json').read_text(encoding='utf-8'))
            self.assertEqual(datos['default_agent'], 'tutor')
            self.assertEqual(datos['model'], 'ollama/' + config['modelo'])
            mcp = datos['mcp']['servers']['ufv-local']
            self.assertFalse(mcp['codemode'])
            self.assertEqual(mcp['command'][-1], str(raiz / 'boveda'))
            for ruta in ('apuntes', 'memoria', 'docs'):
                self.assertIn(ruta, datos['agents']['tutor']['system'])
            self.assertEqual((raiz / 'README.md').read_text(encoding='utf-8'), 'Mi documentación')

    def test_configuracion_previa_del_proyecto_tiene_copia(self):
        with tempfile.TemporaryDirectory() as t:
            raiz = Path(t)
            original = {'model': 'otra/configuracion', 'username': 'alumno'}
            (raiz / 'opencode.json').write_text(json.dumps(original))
            with patch.object(entorno, 'RAIZ', raiz), patch.object(entorno, 'LOCAL', raiz / '.local'):
                entorno.configurar_opencode(entorno_local.perfil(hardware()))
            self.assertEqual(json.loads((raiz / '.local/opencode-original.json').read_text()), original)
            self.assertEqual(json.loads((raiz / 'opencode.json').read_text())['username'], 'alumno')

    def test_5060_16gb_propone_tres_y_contexto_limitado(self):
        p = entorno_local.perfil(hardware())
        self.assertEqual(p['max_agentes'], 3)
        self.assertEqual(p['contexto'], 16384)
        self.assertFalse(p['calibrado'])

    def test_gpu_ocupada_no_se_confunde_con_vram_total(self):
        p = entorno_local.perfil(hardware(libre=1800))
        self.assertEqual((p['max_agentes'], p['acelerador']), (1, 'cpu'))

    def test_2060_6gb_propone_dos(self):
        p = entorno_local.perfil(hardware(vram=6144, libre=5900))
        self.assertEqual(p['max_agentes'], 2)

    def test_el_modelo_del_taller_no_reduce_el_perfil_al_repetir(self):
        h = hardware(vram=6144, libre=3500)
        h['gpu'][0]['reclamable_taller_mb'] = 1400
        self.assertEqual(entorno_local.perfil(h)['max_agentes'], 2)

    def test_cpu_amd_desconocida_y_ram_escasa(self):
        for h in (hardware(tipo=None), hardware(tipo='sin_verificar'), hardware(disponible=2)):
            self.assertEqual(entorno_local.perfil(h)['max_agentes'], 1)

    def test_apple_silicon_usa_ram_compartida(self):
        p = entorno_local.perfil(hardware(tipo='metal', ram=16))
        self.assertEqual((p['max_agentes'], p['acelerador']), (2, 'metal'))

    def test_rechaza_endpoint_externo_y_limites_fuera_de_rango(self):
        with tempfile.TemporaryDirectory() as temporal:
            archivo = Path(temporal) / 'ajustes.json'
            for cambio in ({'url': 'https://servidor.example'}, {'max_agentes': 9}):
                config = dict(entorno_local.perfil(hardware()), **cambio)
                archivo.write_text(json.dumps(config))
                with patch.object(entorno_local, 'AJUSTES', archivo):
                    with self.assertRaises(ValueError):
                        entorno_local.cargar()

    def test_zip_no_puede_escribir_fuera(self):
        with tempfile.TemporaryDirectory() as temporal:
            raiz = Path(temporal)
            archivo = raiz / 'malo.zip'
            with zipfile.ZipFile(archivo, 'w') as paquete:
                paquete.writestr('../fuera.txt', 'no')
            with self.assertRaisesRegex(RuntimeError, 'ruta externa'):
                entorno.extraer(archivo, raiz / 'destino')
            self.assertFalse((raiz / 'fuera.txt').exists())

    def test_calibracion_reduce_a_ultimo_lote_correcto(self):
        p = entorno_local.perfil(hardware())
        cerrojo = threading.Lock()
        estado = {'activas': 0}

        def api(config, ruta, cuerpo=None, **opciones):
            if ruta == '/api/ps':
                return {'models': [{'name': p['modelo'], 'size_vram': 1000}]}
            with cerrojo:
                estado['activas'] += 1
                activas = estado['activas']
            try:
                time.sleep(0.04)
                if activas > 2:
                    raise RuntimeError('Memoria insuficiente simulada')
                return {'message': {'tool_calls': [{'function': {'name': 'eco', 'arguments': {'texto': 'listo'}}}]}}
            finally:
                with cerrojo:
                    estado['activas'] -= 1

        with patch.object(entorno, 'api', side_effect=api):
            entorno.calibrar(p)
        self.assertTrue(p['calibrado'])
        self.assertEqual(p['max_agentes'], 2)
        self.assertFalse(p['calibracion'][-1]['ok'])

    def test_limite_de_peticiones_se_comparte_entre_tareas(self):
        lock = threading.Lock()
        estado = {'activas': 0, 'maximo': 0}

        def pedir(*args, **kwargs):
            with lock:
                estado['activas'] += 1
                estado['maximo'] = max(estado['maximo'], estado['activas'])
            time.sleep(0.03)
            with lock:
                estado['activas'] -= 1
            return {'message': {'role': 'assistant', 'content': 'ok'}}

        with patch.object(nucleo, 'TURNOS', threading.BoundedSemaphore(2)), patch.object(nucleo, 'peticion', side_effect=pedir):
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as grupo:
                list(grupo.map(lambda _: nucleo.chat([], 'simulado', []), range(5)))
        self.assertEqual(estado['maximo'], 2)


if __name__ == '__main__':
    unittest.main()
