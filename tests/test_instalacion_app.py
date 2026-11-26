import hashlib
import json
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from herramientas import instalacion_app as app


class InstalacionApp(unittest.TestCase):
    def paquete(self, raiz, cambios=None):
        contenido = {'preparar.ps1': 'bootstrap', 'iniciar.sh': '#!/bin/sh\n',
                     'nucleo.py': 'codigo inicial', 'boveda/Inicio.md': 'bienvenido'}
        contenido.update(cambios or {})
        archivo = raiz / ('paquete-' + str(len(list(raiz.glob('paquete-*')))) + '.zip')
        with zipfile.ZipFile(archivo, 'w') as z:
            for nombre, texto in contenido.items():
                if texto is not None:
                    z.writestr(app.CARPETA + '/' + nombre, texto)
        return archivo, hashlib.sha256(archivo.read_bytes()).hexdigest()

    def test_rutas_por_usuario_para_los_tres_sistemas(self):
        casa = Path('/personas/Ana')
        self.assertEqual(app.ruta_predeterminada('Windows', {'LOCALAPPDATA': '/datos'}, casa), Path('/datos/Programs/TallerUFV'))
        self.assertEqual(app.ruta_predeterminada('Darwin', {}, casa), casa / 'Library/Application Support/TallerUFV')
        self.assertEqual(app.ruta_predeterminada('Linux', {}, casa), casa / '.local/share/taller-ufv')
        self.assertEqual(app.ruta_predeterminada('Linux', {'XDG_DATA_HOME': '/datos'}, casa), Path('/datos/taller-ufv'))

    def test_actualizacion_conserva_todos_los_datos_y_elimina_codigo_antiguo(self):
        with tempfile.TemporaryDirectory() as t:
            raiz = Path(t)
            zip1, sha1 = self.paquete(raiz, {'viejo.py': 'antiguo'})
            proyecto = app.actualizar_paquete(zip1, raiz / 'app', sha1, '1')
            datos = {'boveda/Inicio.md': 'mi inicio', 'boveda/cursos/Control.md': 'mis apuntes',
                     '.local/ajustes.json': 'ajustes', '.tools/modelo': 'pesos',
                     '.venv/interprete': 'python', 'opencode.json': 'config', 'personal.md': 'mio'}
            for nombre, texto in datos.items():
                p = proyecto / nombre
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(texto)
            zip2, sha2 = self.paquete(raiz, {'nucleo.py': 'codigo nuevo', 'nuevo.py': 'nuevo'})
            self.assertEqual(app.actualizar_paquete(zip2, raiz / 'app', sha2, '2'), proyecto)
            for nombre, texto in datos.items():
                self.assertEqual((proyecto / nombre).read_text(), texto)
            self.assertFalse((proyecto / 'viejo.py').exists())
            self.assertEqual((proyecto / 'nucleo.py').read_text(), 'codigo nuevo')
            self.assertTrue(app.instalacion_valida(proyecto, sha2))
            self.assertFalse(app.instalacion_valida(proyecto, sha1))
            # Reutilizar la instalación no necesita un ZIP, ni ninguna red.
            zip2.unlink()
            self.assertTrue(app.instalacion_valida(proyecto, sha2))

    def test_no_sobrescribe_codigo_editado_ni_archivos_personales(self):
        for editar in (True, False):
            with self.subTest(editar=editar), tempfile.TemporaryDirectory() as t:
                raiz = Path(t)
                z, sha = self.paquete(raiz)
                proyecto = app.actualizar_paquete(z, raiz / 'app', sha, '1')
                objetivo = proyecto / ('nucleo.py' if editar else 'nuevo.py')
                objetivo.write_text('trabajo propio')
                original = (proyecto / app.MARCADOR).read_bytes()
                nuevo, nuevo_sha = self.paquete(raiz, {'nucleo.py': 'actualizado', 'nuevo.py': 'nuevo'})
                with self.assertRaises(ValueError):
                    app.actualizar_paquete(nuevo, raiz / 'app', nuevo_sha, '2')
                self.assertEqual(objetivo.read_text(), 'trabajo propio')
                self.assertEqual((proyecto / app.MARCADOR).read_bytes(), original)

    def test_error_de_escritura_restaura_codigo_y_manifiesto(self):
        with tempfile.TemporaryDirectory() as t:
            raiz = Path(t)
            z, sha = self.paquete(raiz)
            proyecto = app.actualizar_paquete(z, raiz / 'app', sha, '1')
            antes = {p.relative_to(proyecto): p.read_bytes() for p in proyecto.rglob('*') if p.is_file()}
            nuevo, nuevo_sha = self.paquete(raiz, {'nucleo.py': 'nuevo'})
            reemplazar = Path.replace
            fallo = []

            def interrumpir(origen, destino):
                if Path(destino).name == 'nucleo.py' and not fallo:
                    fallo.append(True)
                    raise OSError('Disco simulado sin espacio')
                return reemplazar(origen, destino)

            with patch.object(Path, 'replace', interrumpir), self.assertRaises(OSError):
                app.actualizar_paquete(nuevo, raiz / 'app', nuevo_sha, '2')
            despues = {p.relative_to(proyecto): p.read_bytes() for p in proyecto.rglob('*') if p.is_file()}
            self.assertEqual(antes, despues)
            self.assertTrue(app.instalacion_valida(proyecto, sha))

    def test_zip_externo_enlace_y_hash_incorrecto_se_rechazan(self):
        with tempfile.TemporaryDirectory() as t:
            raiz = Path(t)
            for nombre in ('../fuera', app.CARPETA + '/../fuera', app.CARPETA + '/x\\..\\fuera', app.CARPETA + '/C:/fuera'):
                z, _ = self.paquete(raiz, {nombre: 'no'})
                # Se escribe directamente para probar también rutas fuera del prefijo.
                with zipfile.ZipFile(z, 'a') as paquete:
                    paquete.writestr(nombre, 'prohibido')
                sha = hashlib.sha256(z.read_bytes()).hexdigest()
                with self.subTest(nombre=nombre), self.assertRaises(ValueError):
                    app.actualizar_paquete(z, raiz / 'app', sha, '1')
                self.assertFalse((raiz / 'app' / app.CARPETA).exists())
            z, sha = self.paquete(raiz)
            with self.assertRaises(ValueError):
                app.actualizar_paquete(z, raiz / 'app', 'incorrecto', '1')
            with zipfile.ZipFile(z, 'a') as paquete:
                enlace = zipfile.ZipInfo(app.CARPETA + '/enlace')
                enlace.external_attr = (stat.S_IFLNK | 0o777) << 16
                paquete.writestr(enlace, '../fuera')
            with self.assertRaises(ValueError):
                app.actualizar_paquete(z, raiz / 'app', hashlib.sha256(z.read_bytes()).hexdigest(), '1')

    def test_lanzadores_no_interpolan_rutas_con_espacios(self):
        with tempfile.TemporaryDirectory() as t:
            proyecto = Path(t) / 'Mi carrera'
            componentes = Path(t) / 'Mis ajustes.json'
            with patch.object(app.platform, 'system', return_value='Windows'):
                comando = app.comando_arranque(proyecto, 'preparar', componentes)
                self.assertEqual(comando[-2:], ['-Componentes', str(componentes.resolve())])
                self.assertIn(str(proyecto.resolve() / 'preparar.ps1'), comando)
            with patch.object(app.platform, 'system', return_value='Darwin'):
                comando = app.comando_arranque(proyecto, componentes=componentes)
                self.assertEqual(comando, ['/bin/sh', str(proyecto.resolve() / 'iniciar.sh'), 'iniciar', '--componentes', str(componentes.resolve())])

    def test_accesos_por_usuario_en_tres_sistemas(self):
        with tempfile.TemporaryDirectory() as t:
            raiz = Path(t)
            exe = raiz / 'Instalador con espacios.exe'
            exe.write_bytes(b'binario')
            ambiente = {'APPDATA': str(raiz / 'roaming'), 'XDG_DATA_HOME': str(raiz / 'datos')}
            with patch.object(Path, 'home', return_value=raiz / 'casa'), patch.dict(app.os.environ, ambiente), patch.object(app.subprocess, 'run') as proceso:
                acceso = app.crear_accesos(raiz / 'app', exe, 'Windows')
                self.assertEqual(acceso.name, 'Taller UFV.lnk')
                self.assertIn('--abrir', proceso.call_args.kwargs['env']['UFV_ARGUMENTOS'])
                self.assertTrue(Path(proceso.call_args.kwargs['env']['UFV_LANZADOR']).is_file())
                mac = app.crear_accesos(raiz / 'app', exe, 'Darwin')
                self.assertTrue((mac / 'Contents/Info.plist').is_file())
                self.assertIn('--destino', (mac / 'Contents/MacOS/TallerUFV').read_text())
                linux = app.crear_accesos(raiz / 'app', exe, 'Linux')
                self.assertEqual(linux.parent, raiz / 'datos/applications')
                self.assertIn('Terminal=false', linux.read_text())
                self.assertIn('--abrir', linux.read_text())
                self.assertIn('"', linux.read_text().split('Exec=')[1])

    def test_bundle_mac_se_actualiza_si_solo_cambia_metadata_externa(self):
        with tempfile.TemporaryDirectory() as t:
            raiz = Path(t)
            bundle = raiz / 'Descarga.app'
            ejecutable = bundle / 'Contents/MacOS/Instalador'
            ejecutable.parent.mkdir(parents=True)
            ejecutable.write_bytes(b'ejecutable sin cambios')
            recurso = bundle / 'Contents/Resources/instalador-build.json'
            recurso.parent.mkdir()
            recurso.write_text('{"version":"1"}')
            with patch.object(Path, 'home', return_value=raiz / 'usuario'):
                acceso = app.crear_accesos(raiz / 'app', ejecutable, 'Darwin')
                lanzador1 = (acceso / 'Contents/MacOS/TallerUFV').read_text()
                recurso.write_text('{"version":"2"}')
                app.crear_accesos(raiz / 'app', ejecutable, 'Darwin')
                self.assertNotEqual(lanzador1, (acceso / 'Contents/MacOS/TallerUFV').read_text())
                self.assertEqual(len(list((raiz / 'app/lanzador').glob('*.app'))), 2)


if __name__ == '__main__':
    unittest.main()
