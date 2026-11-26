import hashlib
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from herramientas.importar_carpeta import analizar, importar


def pdf_textual(ruta, texto='El sensor universitario P101 mide presion'):
    from pypdf import PdfWriter
    from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
    escritor = PdfWriter()
    pagina = escritor.add_blank_page(width=600, height=800)
    fuente = DictionaryObject({NameObject('/Type'): NameObject('/Font'),
                              NameObject('/Subtype'): NameObject('/Type1'),
                              NameObject('/BaseFont'): NameObject('/Helvetica')})
    pagina[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): fuente})})
    flujo = DecodedStreamObject()
    flujo.set_data(f'BT /F1 12 Tf 50 700 Td ({texto}) Tj ET'.encode('ascii'))
    pagina[NameObject('/Contents')] = escritor._add_object(flujo)
    with ruta.open('wb') as salida:
        escritor.write(salida)


class ImportarCarpeta(unittest.TestCase):
    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)
        self.raiz = Path(self.temporal.name)
        self.origen = self.raiz / 'Universidad'
        self.origen.mkdir()
        self.boveda = self.raiz / 'boveda'

    def test_preserva_originales_jerarquia_enlaces_y_adjuntos(self):
        (self.origen / 'Segundo' / 'Imagenes').mkdir(parents=True)
        nota = self.origen / 'Segundo' / 'Sensores.md'
        nota.write_text('# Sensores\n[[Otra nota]]\n![Esquema](Imagenes/circuito.png)', encoding='utf-8')
        (nota.parent / 'Otra nota.md').write_text('Otra nota', encoding='utf-8')
        (nota.parent / 'Imagenes' / 'circuito.png').write_bytes(b'PNG imagen')
        (nota.parent / 'calculos.xlsx').write_bytes(b'adjunto binario')
        hashes = {p.relative_to(self.origen): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in self.origen.rglob('*') if p.is_file()}
        progreso = []
        resultado = importar(self.origen, self.boveda, progreso.append)
        destino = Path(resultado['destino'])
        self.assertEqual(resultado['total_archivos'], 4)
        for relativa, digest in hashes.items():
            self.assertEqual(hashlib.sha256((self.origen / relativa).read_bytes()).hexdigest(), digest)
            self.assertEqual(hashlib.sha256((destino / relativa).read_bytes()).hexdigest(), digest)
        self.assertEqual(len(progreso), 4)
        self.assertNotIn('Sensores', '\n'.join(progreso))

    def test_pdf_y_txt_generan_texto_y_conservan_copia(self):
        pdf_textual(self.origen / 'sensores.pdf')
        (self.origen / 'apuntes.txt').write_text('La valvula universitaria necesita calibracion', encoding='utf-8')
        resultado = importar(self.origen, self.boveda)
        destino = Path(resultado['destino'])
        self.assertEqual(resultado['textos_generados'], 2)
        texto = '\n'.join(p.read_text(encoding='utf-8') for p in destino.rglob('*.md'))
        self.assertIn('P101', texto)
        self.assertIn('valvula universitaria', texto)
        self.assertEqual((self.origen / 'sensores.pdf').read_bytes(), (destino / 'sensores.pdf').read_bytes())
        # La búsqueda usa el mismo recorrido que consumen el agente y MCP.
        import nucleo
        self.assertTrue(nucleo.buscar_apuntes('P101', self.boveda)['resultados'])

    def test_pdf_escaneado_y_roto_se_conservan_y_reportan(self):
        from pypdf import PdfWriter
        escritor = PdfWriter()
        escritor.add_blank_page(width=100, height=100)
        with (self.origen / 'escaneado.pdf').open('wb') as salida:
            escritor.write(salida)
        (self.origen / 'roto.pdf').write_bytes(b'esto no es PDF')
        resultado = importar(self.origen, self.boveda)
        self.assertEqual(resultado['pdf_sin_texto'], ['escaneado.pdf'])
        self.assertEqual(len(resultado['errores_extraccion']), 1)
        self.assertTrue((Path(resultado['destino']) / 'roto.pdf').exists())

    def test_repetir_no_sobrescribe_y_reserva_textos_sin_colision(self):
        carpeta = self.origen / '_Texto_consultable'
        carpeta.mkdir()
        (carpeta / 'personal.md').write_text('No tocar', encoding='utf-8')
        (self.origen / 'sensores.txt').write_text('sensor personal', encoding='utf-8')
        primero = Path(importar(self.origen, self.boveda)['destino'])
        (primero / 'mi_nota.md').write_text('Editada después de importar', encoding='utf-8')
        segundo = Path(importar(self.origen, self.boveda)['destino'])
        self.assertNotEqual(primero, segundo)
        self.assertEqual((primero / 'mi_nota.md').read_text(encoding='utf-8'), 'Editada después de importar')
        self.assertTrue((segundo / '_Texto_consultable_' / 'sensores.txt.parte-1.md').exists())
        self.assertEqual((segundo / '_Texto_consultable' / 'personal.md').read_text(encoding='utf-8'), 'No tocar')

    def test_analisis_no_escribe_y_omite_configuracion(self):
        for nombre in ('.obsidian', '.git', 'node_modules'):
            (self.origen / nombre).mkdir()
            (self.origen / nombre / 'privado.md').write_text('no copiar', encoding='utf-8')
        (self.origen / '.secreto').write_text('secreto', encoding='utf-8')
        (self.origen / 'real.md').write_text('real', encoding='utf-8')
        resultado = analizar(self.origen, self.boveda)
        self.assertEqual(resultado['total_archivos'], 1)
        self.assertEqual(len(resultado['omitidos']), 4)
        self.assertFalse(self.boveda.exists())

    def test_rechaza_anidados_raiz_y_home(self):
        with self.assertRaises(ValueError):
            analizar(self.origen, self.origen / 'boveda')
        with self.assertRaises(ValueError):
            analizar(self.origen, self.raiz)
        with self.assertRaises(ValueError):
            analizar(Path.home(), self.boveda)
        with self.assertRaises(ValueError):
            analizar(Path(self.origen.anchor), self.boveda)

    def test_falta_disco_y_fallo_copia_no_dejan_importacion_parcial(self):
        (self.origen / 'nota.md').write_text('sensor', encoding='utf-8')
        with patch('herramientas.importar_carpeta.shutil.disk_usage', return_value=shutil._ntuple_diskusage(100, 99, 1)):
            with self.assertRaises(ValueError):
                importar(self.origen, self.boveda)
        self.assertFalse(self.boveda.exists())
        def interrumpir(_):
            raise RuntimeError('cancelado')
        with self.assertRaises(RuntimeError):
            importar(self.origen, self.boveda, interrumpir)
        self.assertEqual(list((self.boveda / 'apuntes' / 'Importados').iterdir()), [])
        self.assertEqual((self.origen / 'nota.md').read_text(encoding='utf-8'), 'sensor')

    def test_no_sigue_enlace_o_junction_externo(self):
        exterior = self.raiz / 'fuera'
        exterior.mkdir()
        (exterior / 'secreto.md').write_text('secreto', encoding='utf-8')
        (self.origen / 'normal.md').write_text('normal', encoding='utf-8')
        enlace = self.origen / 'enlace'
        try:
            enlace.symlink_to(exterior, target_is_directory=True)
        except OSError:
            if os.name != 'nt':
                self.skipTest('El sistema no permite crear enlaces')
            resultado = subprocess.run(['cmd', '/c', 'mklink', '/J', str(enlace), str(exterior)], capture_output=True)
            self.assertEqual(resultado.returncode, 0)
        self.addCleanup(lambda: enlace.unlink() if enlace.is_symlink() else enlace.rmdir())
        resultado = importar(self.origen, self.boveda)
        self.assertEqual(resultado['total_archivos'], 1)
        self.assertTrue(any(p['motivo'] == 'enlace o junction' for p in resultado['omitidos']))
        self.assertFalse((Path(resultado['destino']) / 'enlace').exists())
        with self.assertRaises(ValueError):
            analizar(enlace, self.boveda)

    def test_destino_con_enlace_o_junction_no_escribe_fuera(self):
        exterior = self.raiz / 'ajena'
        exterior.mkdir()
        self.boveda.mkdir()
        (self.origen / 'normal.md').write_text('normal', encoding='utf-8')
        enlace = self.boveda / 'apuntes'
        try:
            enlace.symlink_to(exterior, target_is_directory=True)
        except OSError:
            if os.name != 'nt':
                self.skipTest('El sistema no permite crear enlaces')
            resultado = subprocess.run(['cmd', '/c', 'mklink', '/J', str(enlace), str(exterior)], capture_output=True)
            self.assertEqual(resultado.returncode, 0)
        self.addCleanup(lambda: enlace.unlink() if enlace.is_symlink() else enlace.rmdir())
        with self.assertRaises(ValueError):
            importar(self.origen, self.boveda)
        self.assertEqual(list(exterior.iterdir()), [])


if __name__ == '__main__':
    unittest.main()
