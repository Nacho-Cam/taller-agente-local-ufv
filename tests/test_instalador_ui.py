import hashlib
import io
import json
import queue
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import Mock, patch

from herramientas import instalador_ui as ui


OPCIONES = dict(escritorio=True, obsidian=False, opencode=True, calibrar=False)


def paquete():
    archivo = io.BytesIO()
    with zipfile.ZipFile(archivo, 'w') as z:
        for nombre in ('preparar.ps1', 'iniciar.sh', 'boveda/Inicio.md'):
            z.writestr(ui.CARPETA + '/' + nombre, '# prueba\n')
    return archivo.getvalue()


class FlujoInstalador(unittest.TestCase):
    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)
        self.destino = Path(self.temporal.name) / 'Mi universidad'
        self.datos = paquete()
        self.meta = dict(version='prueba', url='https://example.invalid/paquete.zip',
                         sha256=hashlib.sha256(self.datos).hexdigest())
        self.app = ui.Instalador.__new__(ui.Instalador)
        self.app.meta = self.meta
        self.app.eventos = queue.Queue()
        self.app.log_archivo = None
        self.app.proceso = None

    def instalado(self, opciones=OPCIONES):
        origen = Path(self.temporal.name) / 'paquete.zip'
        origen.write_bytes(self.datos)
        proyecto = ui.actualizar_paquete(origen, self.destino, self.meta['sha256'], 'prueba')
        local = proyecto / '.local'
        local.mkdir()
        (local / 'componentes.json').write_text(json.dumps(opciones))
        (local / 'ajustes.json').write_text('{}')
        return proyecto

    def backend(self, comando, proyecto):
        if comando[1] == 'preparar':
            seleccion = Path(comando[2])
            (proyecto / '.local/componentes.json').write_text(seleccion.read_text())
            (proyecto / '.local/ajustes.json').write_text('{}')

    def ejecutar_flujo(self, opciones, accion, red=False):
        ejecutar = Mock(side_effect=self.backend)
        self.app.ejecutar = ejecutar
        comando = lambda proyecto, accion='iniciar', componentes=None: ['backend', accion] + ([str(componentes)] if componentes else [])
        respuesta = io.BytesIO(self.datos) if red else None
        with patch.object(ui, 'comando_arranque', side_effect=comando), patch.object(ui, 'urlopen', return_value=respuesta) as descargar, patch.object(ui, 'crear_accesos'), patch.object(ui, 'abrir_terminal') as terminal, patch.object(ui.sys, 'frozen', False, create=True):
            self.app.trabajar(self.destino, dict(opciones), accion)
        eventos = []
        while not self.app.eventos.empty():
            eventos.append(self.app.eventos.get_nowait())
        return ejecutar, descargar, terminal, eventos

    def test_primera_instalacion_pipeline_real_zip_y_seleccion(self):
        ejecutar, descargar, _, eventos = self.ejecutar_flujo(OPCIONES, 'preparar', red=True)
        self.assertEqual(descargar.call_count, 1)
        self.assertEqual([c.args[0][1] for c in ejecutar.call_args_list], ['preparar'])
        proyecto = self.destino / ui.CARPETA
        self.assertEqual(ui.preferencias(self.destino), OPCIONES)
        self.assertTrue((proyecto / 'boveda/Inicio.md').is_file())
        self.assertEqual(eventos[-1][0], 'fin', eventos)

    def test_abrir_existente_no_prepara_ni_descarga_ni_pasa_componentes(self):
        proyecto = self.instalado()
        ejecutar, descargar, _, eventos = self.ejecutar_flujo(OPCIONES, 'iniciar')
        descargar.assert_not_called()
        self.assertEqual([c.args[0] for c in ejecutar.call_args_list], [['backend', 'iniciar']])
        self.assertEqual(ejecutar.call_args.args[1], proyecto)
        self.assertEqual(eventos[-1][0], 'fin', eventos)

    def test_cambiar_componentes_prepara_una_vez_y_luego_abre_sin_repreparar(self):
        self.instalado(dict(OPCIONES, obsidian=True))
        ejecutar, descargar, _, eventos = self.ejecutar_flujo(OPCIONES, 'iniciar')
        descargar.assert_not_called()
        self.assertEqual([c.args[0][1] for c in ejecutar.call_args_list], ['preparar', 'iniciar'])
        self.assertEqual(ejecutar.call_args_list[-1].args[0], ['backend', 'iniciar'])
        self.assertEqual(ui.preferencias(self.destino), OPCIONES)
        self.assertEqual(eventos[-1][0], 'fin', eventos)

    def test_terminal_existente_arranca_sin_preparar_en_tuberia(self):
        opciones = dict(OPCIONES, escritorio=False)
        proyecto = self.instalado(opciones)
        ejecutar, descargar, terminal, eventos = self.ejecutar_flujo(opciones, 'iniciar')
        descargar.assert_not_called()
        ejecutar.assert_not_called()
        terminal.assert_called_once_with(proyecto, None)
        self.assertEqual(eventos[-1][0], 'fin', eventos)

    def test_error_no_finaliza_como_exito_y_reintento_reusa_archivos(self):
        self.instalado()
        self.app.ejecutar = Mock(side_effect=RuntimeError('Disco lleno'))
        with patch.object(ui, 'urlopen', side_effect=AssertionError('No descargar')), patch.object(ui.sys, 'frozen', False, create=True):
            self.app.trabajar(self.destino, dict(OPCIONES), 'preparar')
        eventos = list(self.app.eventos.queue)
        self.assertEqual(eventos[-1], ('error', 'Disco lleno'))
        self.assertFalse(any(e[0] == 'fin' for e in eventos))
        while not self.app.eventos.empty():
            self.app.eventos.get_nowait()
        ejecutar, descargar, _, eventos = self.ejecutar_flujo(OPCIONES, 'preparar')
        descargar.assert_not_called()
        self.assertEqual(ejecutar.call_count, 1)
        self.assertEqual(eventos[-1][0], 'fin', eventos)

    def test_checksum_erroneo_no_ejecuta_codigo_descargado(self):
        self.meta['sha256'] = '0' * 64
        ejecutar, _, _, eventos = self.ejecutar_flujo(OPCIONES, 'preparar', red=True)
        ejecutar.assert_not_called()
        self.assertEqual(eventos[-1][0], 'error')
        self.assertIn('SHA256', eventos[-1][1])

    def test_configuracion_ausente_prepara_antes_de_abrir(self):
        proyecto = self.instalado()
        (proyecto / '.local/ajustes.json').unlink()
        ejecutar, descargar, _, eventos = self.ejecutar_flujo(OPCIONES, 'iniciar')
        descargar.assert_not_called()
        self.assertEqual([c.args[0][1] for c in ejecutar.call_args_list], ['preparar', 'iniciar'])
        self.assertEqual(ejecutar.call_args_list[-1].args[0], ['backend', 'iniciar'])
        self.assertEqual(eventos[-1][0], 'fin', eventos)

    def test_codigo_modificado_no_se_ejecuta_ni_se_reemplaza(self):
        proyecto = self.instalado()
        lanzador = proyecto / 'preparar.ps1'
        lanzador.write_text('# Mis cambios personales')
        ejecutar, descargar, _, eventos = self.ejecutar_flujo(OPCIONES, 'iniciar')
        ejecutar.assert_not_called()
        descargar.assert_not_called()
        self.assertEqual(eventos[-1][0], 'error')
        self.assertEqual(lanzador.read_text(), '# Mis cambios personales')

    def test_preferencias_rechaza_desktop_sin_cli_y_claves_extras(self):
        proyecto = self.instalado()
        for datos in (dict(OPCIONES, opencode=False), dict(OPCIONES, desconocido=True)):
            with self.subTest(datos=datos):
                (proyecto / '.local/componentes.json').write_text(json.dumps(datos))
                with self.assertRaises(ValueError):
                    ui.preferencias(self.destino)


class InteraccionTk(unittest.TestCase):
    def setUp(self):
        try:
            self.raiz = ui.tk.Tk()
        except ui.tk.TclError as error:
            self.skipTest('Tk necesita una sesión gráfica: ' + str(error))
        self.raiz.withdraw()
        self.addCleanup(self.raiz.destroy)
        self.temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)
        self.destino = Path(self.temporal.name) / 'Taller'
        self.app = ui.Instalador(self.raiz, dict(version='prueba', sha256='0' * 64, url='https://example.invalid'), self.destino)

    def test_dependencia_de_checkboxes_desktop_cli(self):
        self.app.opciones['opencode'].set(False)
        self.app.cambiar_opcion('opencode')
        self.assertFalse(self.app.opciones['escritorio'].get())
        self.app.opciones['escritorio'].set(True)
        self.app.cambiar_opcion('escritorio')
        self.assertTrue(self.app.opciones['opencode'].get())

    def test_error_permite_reintentar_y_libera_controles(self):
        self.app.ocupado = True
        self.app.eventos.put(('error', 'No hay conexión'))
        self.app.recibir()
        self.assertFalse(self.app.ocupado)
        self.assertEqual(self.app.instalar.cget('text'), 'Reintentar instalación')
        self.assertEqual(str(self.app.instalar.cget('state')), 'normal')
        self.assertIn('No hay conexión', self.app.log.get('1.0', 'end'))

    def test_log_sin_permisos_no_interrumpe_la_interfaz(self):
        self.app.log_archivo = Path(self.temporal.name) / 'carpeta-ausente' / 'log.txt'
        self.app.ocupado = True
        self.app.eventos.put(('fin', 'Listo'))
        self.app.recibir()
        self.assertFalse(self.app.ocupado)
        self.assertEqual(str(self.app.instalar.cget('state')), 'normal')

    def test_carpeta_invalida_no_arranca_hilo_ni_bloquea_controles(self):
        self.app.destino.set('ruta relativa')
        with patch.object(ui.messagebox, 'showerror') as error, patch.object(ui.threading, 'Thread') as hilo:
            self.app.iniciar('preparar')
        error.assert_called_once()
        hilo.assert_not_called()
        self.assertFalse(self.app.ocupado)

    def test_cambiar_ruta_recarga_eleccion_de_esa_instalacion(self):
        otra = Path(self.temporal.name) / 'Otro taller'
        local = otra / ui.CARPETA / '.local'
        local.mkdir(parents=True)
        opciones = dict(escritorio=False, opencode=False, obsidian=False, calibrar=False)
        (local / 'componentes.json').write_text(json.dumps(opciones))
        self.app.destino.set(str(otra))
        self.app.cargar_preferencias()
        self.assertEqual({k: v.get() for k, v in self.app.opciones.items()}, opciones)

    def test_no_duplica_trabajo_al_pulsar_mientras_esta_ocupado(self):
        self.app.ocupado = True
        with patch.object(ui.threading, 'Thread') as hilo:
            self.app.iniciar('preparar')
            self.app.iniciar('iniciar')
        hilo.assert_not_called()


if __name__ == '__main__':
    unittest.main()
