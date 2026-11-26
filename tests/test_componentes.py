import argparse
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from herramientas import entorno, opencode_desktop


def argumentos(**cambios):
    return argparse.Namespace(**dict(dict(componentes=None, solo_detectar=False, sin_obsidian=False,
                                          sin_calibrar=False, sin_opencode=False, ui='auto', accion='iniciar'), **cambios))


class Componentes(unittest.TestCase):
    def test_reconfigurar_o_retomar_no_exige_espacio_de_primera_descarga(self):
        for estado, libre, mensaje in [('nuevo', 5, '7 GB'), ('preparado', 5, 'continuar'),
                                       ('parcial', 5, 'continuar'), ('preparado', 2, '3 GB')]:
            with self.subTest(estado=estado, libre=libre), tempfile.TemporaryDirectory() as t:
                raiz = Path(t)
                ajustes = raiz / 'ajustes.json'
                tools = raiz / 'tools'
                if estado == 'preparado':
                    ajustes.write_text('{}')
                elif estado == 'parcial':
                    marcador = tools / 'ollama' / entorno.OLLAMA_VERSION / 'ejecutable.txt'
                    marcador.parent.mkdir(parents=True)
                    marcador.write_text('ollama')
                with patch.object(entorno, 'RAIZ', raiz), patch.object(entorno, 'LOCAL', raiz), patch.object(entorno, 'TOOLS', tools), patch.object(entorno.entorno, 'AJUSTES', ajustes), patch.object(entorno.entorno, 'detectar', return_value={}), patch.object(entorno.entorno, 'perfil', return_value={'hardware': {}}), patch.object(entorno.shutil, 'disk_usage', return_value=argparse.Namespace(free=libre * 1024**3)), patch.object(entorno, 'instalar_ollama', side_effect=RuntimeError('continuar')), patch('builtins.print'):
                    with self.assertRaisesRegex(RuntimeError, mensaje):
                        entorno.preparar(argumentos(sin_obsidian=True))

    def test_guarda_eleccion_y_no_vuelve_a_preguntar_al_reabrir(self):
        with tempfile.TemporaryDirectory() as t:
            raiz = Path(t)
            datos = dict(escritorio=True, obsidian=False, opencode=True, calibrar=False)
            origen = raiz / 'eleccion.json'
            origen.write_text(json.dumps(datos), encoding='utf-8')
            with patch.object(entorno, 'LOCAL', raiz / '.local'), patch.object(opencode_desktop, 'elegir', side_effect=AssertionError('Sin preguntas')):
                args = argumentos(componentes=str(origen))
                self.assertTrue(entorno.resolver_componentes(args))
                self.assertTrue(args.sin_obsidian)
                self.assertTrue(args.sin_calibrar)
                self.assertEqual(json.loads((raiz / '.local/componentes.json').read_text()), datos)
                origen.unlink()
                otros = argumentos()
                self.assertTrue(entorno.resolver_componentes(otros))
                self.assertTrue(otros.sin_obsidian)

    def test_indicadores_explicitos_prevalecen_sin_cambiar_seleccion_guardada(self):
        with tempfile.TemporaryDirectory() as t:
            raiz = Path(t)
            datos = dict(escritorio=True, obsidian=True, opencode=True, calibrar=True)
            archivo = raiz / 'componentes.json'
            archivo.write_text(json.dumps(datos), encoding='utf-8')
            with patch.object(entorno, 'LOCAL', raiz), patch.object(opencode_desktop, 'elegir', return_value=False) as elegir:
                args = argumentos(sin_obsidian=True, sin_calibrar=True, sin_opencode=True)
                self.assertFalse(entorno.resolver_componentes(args))
                elegir.assert_not_called()
                self.assertTrue(args.sin_obsidian)
                self.assertTrue(args.sin_calibrar)
                args = argumentos(ui='no')
                self.assertFalse(entorno.resolver_componentes(args))
                elegir.assert_called_once_with('no')
                self.assertEqual(json.loads(archivo.read_text()), datos)

    def test_ui_si_habilita_cli_previamente_desmarcada(self):
        with tempfile.TemporaryDirectory() as t:
            raiz = Path(t)
            (raiz / 'componentes.json').write_text(json.dumps(dict(escritorio=False, obsidian=False, opencode=False, calibrar=False)))
            with patch.object(entorno, 'LOCAL', raiz), patch.object(opencode_desktop, 'elegir', return_value=True):
                args = argumentos(ui='si')
                self.assertTrue(entorno.resolver_componentes(args))
                self.assertFalse(args.sin_opencode)

    def test_sin_seleccion_previa_conserva_menu_y_no_crea_archivo(self):
        with tempfile.TemporaryDirectory() as t, patch.object(entorno, 'LOCAL', Path(t)), patch.object(opencode_desktop, 'elegir', return_value=False) as elegir:
            args = argumentos()
            self.assertFalse(entorno.resolver_componentes(args))
            elegir.assert_called_once_with('auto')
            self.assertFalse((Path(t) / 'componentes.json').exists())

    def test_rechaza_json_incompleto_tipos_incorrectos_y_dependencia_desktop(self):
        casos = [[], {}, dict(escritorio=True, obsidian=False, opencode=False, calibrar=False),
                 dict(escritorio=False, obsidian='no', opencode=True, calibrar=True)]
        with tempfile.TemporaryDirectory() as t:
            raiz = Path(t)
            origen = raiz / 'entrada.json'
            with patch.object(entorno, 'LOCAL', raiz / '.local'):
                for datos in casos:
                    with self.subTest(datos=datos):
                        origen.write_text(json.dumps(datos))
                        with self.assertRaises(ValueError):
                            entorno.resolver_componentes(argumentos(componentes=str(origen)))
                self.assertFalse((raiz / '.local/componentes.json').exists())

    def test_solo_detectar_no_guarda_la_eleccion(self):
        with tempfile.TemporaryDirectory() as t:
            raiz = Path(t)
            origen = raiz / 'entrada.json'
            origen.write_text(json.dumps(dict(escritorio=False, obsidian=False, opencode=False, calibrar=False)))
            with patch.object(entorno, 'LOCAL', raiz / '.local'):
                self.assertFalse(entorno.resolver_componentes(argumentos(componentes=str(origen), solo_detectar=True)))
                self.assertFalse((raiz / '.local').exists())

    def test_reabrir_sin_extras_no_reutiliza_cli_antiguo_ni_instala_aplicaciones(self):
        with tempfile.TemporaryDirectory() as t:
            raiz = Path(t)
            (raiz / 'componentes.json').write_text(json.dumps(dict(escritorio=False, obsidian=False, opencode=False, calibrar=False)))
            ajustes = raiz / 'ajustes.json'
            ajustes.write_text('{}')
            config = dict(hardware={'sistema': 'Windows'}, opencode_bin='antiguo.exe', opencode_desktop_bin='Desktop.exe')
            with patch.object(entorno, 'LOCAL', raiz), patch.object(entorno.entorno, 'AJUSTES', ajustes), patch.object(entorno.entorno, 'cargar', return_value=config), patch.object(entorno.entorno, 'guardar'), patch.object(entorno, 'servidor'), patch.object(entorno, 'configurar_opencode'), patch.object(entorno, 'preparar', side_effect=AssertionError('No descargar otra vez')), patch('herramientas.obsidian_local.instalar', side_effect=AssertionError('No instalar Obsidian')), patch.object(opencode_desktop, 'instalar', side_effect=AssertionError('No instalar Desktop')), patch.object(entorno.subprocess, 'call', return_value=0) as iniciar, patch.object(entorno.sys, 'argv', ['entorno', 'iniciar']):
                self.assertEqual(entorno.main(), 0)
                self.assertTrue(iniciar.call_args.args[0][-1].endswith('agente.py'))
                self.assertNotIn('opencode_bin', config)

    def test_preparar_no_instala_componentes_desmarcados(self):
        with tempfile.TemporaryDirectory() as t:
            raiz = Path(t)
            seleccion = dict(escritorio=False, obsidian=False, opencode=False, calibrar=False)
            (raiz / 'componentes.json').write_text(json.dumps(seleccion))
            config = dict(hardware={}, modelo='prueba', contexto=4096, max_agentes=1, avisos=[])
            with patch.object(entorno, 'LOCAL', raiz), patch.object(entorno, 'RAIZ', raiz), patch.object(entorno.entorno, 'detectar', return_value={}), patch.object(entorno.entorno, 'perfil', return_value=config), patch.object(entorno.entorno, 'guardar'), patch.object(entorno.shutil, 'disk_usage', return_value=argparse.Namespace(free=20 * 1024**3)), patch.object(entorno, 'instalar_ollama', return_value='ollama'), patch.object(entorno, 'instalar_opencode', side_effect=AssertionError('No descargar CLI')), patch('herramientas.obsidian_local.instalar', side_effect=AssertionError('No descargar Obsidian')), patch.object(opencode_desktop, 'instalar', side_effect=AssertionError('No descargar Desktop')), patch.object(entorno, 'servidor'), patch.object(entorno, 'descargar_modelo'), patch.object(entorno, 'api', return_value={'capabilities': ['tools']}), patch.object(entorno, 'calibrar', side_effect=AssertionError('No calibrar')), patch.object(entorno, 'configurar_opencode'):
                args = argumentos(accion='preparar')
                self.assertFalse(entorno.resolver_componentes(args))
                resultado = entorno.preparar(args)
                self.assertNotIn('opencode_bin', resultado)
                self.assertNotIn('obsidian_bin', resultado)


if __name__ == '__main__':
    unittest.main()
