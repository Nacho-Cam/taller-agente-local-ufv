import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from herramientas.instalador_windows import CARPETA, extraer_paquete
from herramientas import obsidian_local
from herramientas import instalador_windows


class InstaladorWindows(unittest.TestCase):
    def test_arranque_instalado_no_necesita_red(self):
        with tempfile.TemporaryDirectory() as t:
            raiz = Path(t)
            proyecto = raiz / CARPETA
            proyecto.mkdir()
            (proyecto / 'preparar.ps1').write_text('contenido')
            (proyecto / '.ufv-paquete.json').write_text(json.dumps({'sha256': 'abc'}))
            (raiz / 'instalador-build.json').write_text(json.dumps({'version': 'prueba', 'sha256': 'abc', 'url': 'https://example.invalid'}))
            with patch.object(instalador_windows.sys, '_MEIPASS', str(raiz), create=True), patch.object(instalador_windows.sys, 'argv', ['instalador', '--destino', str(raiz), '--accion', 'notas']), patch.object(instalador_windows, 'urlopen', side_effect=AssertionError('No debe descargar')), patch.object(instalador_windows.subprocess, 'call', return_value=0):
                self.assertEqual(instalador_windows.main(), 0)

    def paquete(self, raiz, nombres):
        archivo = raiz / 'paquete.zip'
        with zipfile.ZipFile(archivo, 'w') as z:
            for nombre in nombres:
                z.writestr(nombre, 'contenido')
        return archivo, hashlib.sha256(archivo.read_bytes()).hexdigest()

    def test_repetir_conserva_notas_y_otra_version_no_sobrescribe(self):
        with tempfile.TemporaryDirectory() as t:
            raiz = Path(t)
            archivo, sha = self.paquete(raiz, [CARPETA + '/preparar.ps1'])
            proyecto = extraer_paquete(archivo, raiz / 'destino', sha)
            nota = proyecto / 'personal.md'
            nota.write_text('mi nota')
            self.assertEqual(extraer_paquete(archivo, raiz / 'destino', sha), proyecto)
            self.assertEqual(nota.read_text(), 'mi nota')
            otro, otro_sha = self.paquete(raiz, [CARPETA + '/preparar.ps1', CARPETA + '/nuevo.md'])
            with self.assertRaises(ValueError):
                extraer_paquete(otro, raiz / 'destino', otro_sha)
            self.assertEqual(nota.read_text(), 'mi nota')

    def test_hash_y_rutas_externas_se_rechazan(self):
        with tempfile.TemporaryDirectory() as t:
            raiz = Path(t)
            archivo, sha = self.paquete(raiz, [CARPETA + '/preparar.ps1', '../fuera.txt'])
            with self.assertRaises(ValueError):
                extraer_paquete(archivo, raiz / 'destino', '0' * 64)
            with self.assertRaises(ValueError):
                extraer_paquete(archivo, raiz / 'destino', sha)
            self.assertFalse((raiz / 'fuera.txt').exists())

    def test_obsidian_abre_nota_solo_en_boveda_ya_registrada(self):
        with tempfile.TemporaryDirectory() as t:
            raiz = Path(t)
            vault = raiz / 'mis apuntes'
            vault.mkdir()
            registro = raiz / 'obsidian.json'
            registro.write_text(json.dumps({'vaults': {'uno': {'path': str(vault)}}}))
            with patch.object(obsidian_local, 'registro', return_value=registro), patch.object(obsidian_local, 'lanzar') as lanzar:
                self.assertTrue(obsidian_local.abrir('Obsidian.exe', 'Windows', vault))
                self.assertIn('obsidian://open?path=', lanzar.call_args.args[2])
            registro.write_text('{"vaults":{}}')
            with patch.object(obsidian_local, 'registro', return_value=registro), patch.object(obsidian_local, 'lanzar') as lanzar, patch.object(obsidian_local, 'cerrar_para_registrar'):
                self.assertTrue(obsidian_local.abrir('Obsidian.exe', 'Windows', vault))
                self.assertTrue(obsidian_local.boveda_conocida('Windows', vault))

    def test_registro_conserva_otras_bovedas_y_copia_original(self):
        with tempfile.TemporaryDirectory() as t:
            raiz = Path(t)
            registro = raiz / 'obsidian.json'
            original = json.dumps({'vaults': {'otra': {'path': str(raiz / 'otra'), 'open': True}}, 'opcion': 'conservar'})
            registro.write_text(original)
            with patch.object(obsidian_local, 'registro', return_value=registro), patch.object(obsidian_local, 'cerrar_para_registrar'):
                obsidian_local.registrar_boveda('Windows', 'Obsidian.exe', raiz / 'taller')
                obsidian_local.registrar_boveda('Windows', 'Obsidian.exe', raiz / 'taller')
            datos = json.loads(registro.read_text())
            self.assertEqual(len(datos['vaults']), 2)
            self.assertEqual(datos['opcion'], 'conservar')
            self.assertTrue(datos['vaults']['otra']['open'])
            self.assertEqual((raiz / 'obsidian.json.ufv-backup').read_text(), original)
