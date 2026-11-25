import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from herramientas import opencode_desktop as desktop
from herramientas import entorno, instalador_windows


class Interfaz(unittest.TestCase):
    def test_elegir_y_recordar_sin_volver_a_preguntar(self):
        with tempfile.TemporaryDirectory() as t, patch.object(desktop, 'PREFERENCIAS', Path(t) / 'interfaz.json'):
            with patch.object(desktop.sys.stdin, 'isatty', return_value=True), patch('builtins.input', side_effect=['incorrecto', '1']):
                self.assertTrue(desktop.elegir())
            with patch('builtins.input', side_effect=AssertionError('No debe preguntar')):
                self.assertTrue(desktop.elegir())
            self.assertFalse(desktop.elegir('no'))
            self.assertFalse(desktop.elegir())

    def test_automatizado_no_instala_ni_guarda_una_eleccion_implicita(self):
        with tempfile.TemporaryDirectory() as t, patch.object(desktop, 'PREFERENCIAS', Path(t) / 'interfaz.json'):
            with patch.object(desktop.sys.stdin, 'isatty', return_value=False):
                self.assertFalse(desktop.elegir())
            self.assertFalse(desktop.PREFERENCIAS.exists())
            self.assertTrue(desktop.elegir('si'))

    def test_enlace_abre_proyecto_con_espacios_y_no_usa_shell(self):
        with patch.object(desktop.subprocess, 'Popen') as lanzar:
            desktop.abrir('OpenCode.exe', 'Windows', Path('mis apuntes'))
        argumentos = lanzar.call_args.args[0]
        self.assertEqual(argumentos[0], 'OpenCode.exe')
        self.assertTrue(argumentos[1].startswith('opencode://open-project?directory='))
        self.assertIn('mis%20apuntes', argumentos[1])
        self.assertNotIn('shell', lanzar.call_args.kwargs)

    def test_solo_terminal_no_instala_desktop_y_si_respeta_config(self):
        config = {'hardware': {'sistema': 'Windows'}, 'opencode_bin': 'cli.exe', 'interfaz': 'opencode'}
        with tempfile.TemporaryDirectory() as t:
            raiz = Path(t)
            ajustes = raiz / 'ajustes.json'
            ajustes.write_text('{}')
            with patch.object(entorno.entorno, 'AJUSTES', ajustes), patch.object(entorno.entorno, 'cargar', return_value=config), patch.object(entorno.entorno, 'guardar'), patch.object(entorno, 'servidor'), patch.object(entorno, 'configurar_opencode', return_value=raiz), patch.object(entorno.subprocess, 'call', return_value=0) as cli, patch.object(desktop, 'instalar', side_effect=AssertionError('No instalar UI')), patch.object(desktop, 'PREFERENCIAS', raiz / 'ui.json'), patch.object(entorno.sys, 'argv', ['entorno', 'iniciar', '--ui', 'no', '--sin-obsidian']):
                self.assertEqual(entorno.main(), 0)
                self.assertIn('mini', cli.call_args.args[0])

    def test_desktop_se_instala_y_abre_sin_arrancar_chat_terminal(self):
        config = {'hardware': {'sistema': 'Windows'}, 'opencode_bin': 'cli.exe', 'interfaz': 'opencode'}
        with tempfile.TemporaryDirectory() as t:
            raiz = Path(t)
            ajustes = raiz / 'ajustes.json'
            ajustes.write_text('{}')
            with patch.object(entorno.entorno, 'AJUSTES', ajustes), patch.object(entorno.entorno, 'cargar', return_value=config), patch.object(entorno.entorno, 'guardar'), patch.object(entorno, 'servidor'), patch.object(entorno, 'configurar_opencode', return_value=raiz), patch.object(entorno.subprocess, 'call', side_effect=AssertionError('No abrir terminal')), patch.object(desktop, 'instalar', return_value='Desktop.exe') as instalar, patch.object(desktop, 'abrir') as abrir, patch.object(desktop, 'PREFERENCIAS', raiz / 'ui.json'), patch.object(entorno.sys, 'argv', ['entorno', 'iniciar', '--ui', 'si', '--sin-obsidian']):
                self.assertEqual(entorno.main(), 0)
                instalar.assert_called_once()
                abrir.assert_called_once_with('Desktop.exe', 'Windows', raiz)


if __name__ == '__main__':
    unittest.main()
