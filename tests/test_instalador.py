import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from herramientas.instalador_windows import CARPETA, extraer_paquete
from herramientas import obsidian_local


class InstaladorWindows(unittest.TestCase):
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
            with patch.object(obsidian_local, 'registro', return_value=registro), patch.object(obsidian_local.subprocess, 'Popen') as lanzar:
                self.assertTrue(obsidian_local.abrir('Obsidian.exe', 'Windows', vault))
                self.assertIn('obsidian://open?path=', lanzar.call_args.args[0][1])
            registro.write_text('{"vaults":{}}')
            with patch.object(obsidian_local, 'registro', return_value=registro), patch.object(obsidian_local.subprocess, 'Popen') as lanzar:
                self.assertFalse(obsidian_local.abrir('Obsidian.exe', 'Windows', vault))
                self.assertEqual(lanzar.call_args.args[0][1], 'obsidian://choose-vault')
