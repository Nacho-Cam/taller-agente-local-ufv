import asyncio
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from academia import Academia, NOMBRES
import nucleo
from mcp import Client
from mcp.client.stdio import StdioServerParameters


class Carrera(unittest.TestCase):
    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)
        self.raiz = Path(self.temporal.name)
        self.a = Academia(self.raiz)
        self.c = self.a.crear_curso('2026-2027 tercero')['id']
        self.s = self.a.crear_asignatura(self.c, 'Automatización')['id']

    def test_asignaturas_por_curso_no_se_mezclan_y_no_sobrescriben(self):
        otro = self.a.crear_curso('2025-2026 segundo')['id']
        self.a.crear_asignatura(otro, 'Automatización')
        self.assertFalse(self.a.crear_asignatura(self.c, 'Automatizacion')['creada'])
        self.a.anadir_material(self.c, self.s, 'tema', 'Sensores', 'P-101 es un sensor de presión')
        self.assertEqual(len(self.a.listar_carrera(self.c, self.s)['cursos'][0]['asignaturas'][0]['materiales']), 1)
        self.assertEqual(self.a.listar_carrera(otro, self.s)['cursos'][0]['asignaturas'][0]['materiales'], [])
        self.assertFalse(nucleo.buscar_apuntes('sensor presión', self.raiz, curso=otro, asignatura=self.s)['resultados'])
        self.assertTrue(nucleo.buscar_apuntes('sensor presión', self.raiz, curso=self.c, asignatura=self.s)['resultados'])

    def test_ciclo_tarea_agenda_estados_y_examen(self):
        tarea = self.a.anadir_material(self.c, self.s, 'tarea', 'Práctica 1', fecha='2020-01-02', tema='Sensores')
        self.a.anadir_material(self.c, self.s, 'examen', 'Parcial', fecha='2099-12-12')
        agenda = self.a.consultar_agenda(self.c)['pendientes']
        self.assertEqual([m['titulo'] for m in agenda], ['Práctica 1', 'Parcial'])
        self.assertTrue(agenda[0]['vencido'])
        self.a.actualizar_tarea(self.c, self.s, tarea['id'], 'completado')
        self.assertEqual(len(self.a.consultar_agenda()['pendientes']), 1)
        self.assertIn('Parcial', (self.raiz / 'Carrera.md').read_text(encoding='utf-8'))

    def test_archivar_restaurar_no_borra_y_no_aparece_en_busqueda(self):
        material = self.a.anadir_material(self.c, self.s, 'apunte', 'Medición', 'Sensor farolillo diferencial')
        self.assertTrue(nucleo.buscar_apuntes('farolillo', self.raiz)['resultados'])
        archivado = self.a.quitar_asignatura(self.c, self.s)
        self.assertTrue((self.raiz / archivado['papelera']).is_dir())
        self.assertFalse(nucleo.buscar_apuntes('farolillo', self.raiz)['resultados'])
        self.a.restaurar_asignatura(self.c, self.s)
        self.assertTrue((self.raiz / material['archivo']).is_file())
        self.assertTrue(nucleo.buscar_apuntes('farolillo', self.raiz)['resultados'])
        self.a.quitar_material(self.c, self.s, material['id'])
        self.assertFalse(nucleo.buscar_apuntes('farolillo', self.raiz)['resultados'])

    def test_no_restaurar_sobre_asignatura_activa(self):
        self.a.quitar_asignatura(self.c, self.s)
        self.a.crear_asignatura(self.c, 'Automatización')
        with self.assertRaises(ValueError):
            self.a.restaurar_asignatura(self.c, self.s)

    def test_busqueda_con_ancestro_alias_conserva_limites_de_boveda(self):
        datos = self.raiz / 'datos'
        datos.mkdir()
        alias = self.raiz / 'alias-datos'
        try:
            alias.symlink_to(datos, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest('El equipo no permite crear enlaces simbólicos de prueba.')
        boveda = alias / 'boveda'
        academia = Academia(boveda)
        curso = academia.crear_curso('2026-2027')['id']
        asignatura = academia.crear_asignatura(curso, 'Control')['id']
        material = academia.anadir_material(curso, asignatura, 'tema', 'Sensores', 'sensor farolillo')
        apuntes = boveda / 'apuntes'
        apuntes.mkdir()
        (apuntes / 'lectura.md').write_text('sensor farolillo', encoding='utf-8')
        resultados = nucleo.buscar_apuntes('farolillo', boveda)['resultados']
        self.assertEqual({r['fuente'] for r in resultados}, {material['archivo'], 'apuntes/lectura.md'})
        filtrados = nucleo.buscar_apuntes('farolillo', boveda, curso=curso, asignatura=asignatura)['resultados']
        self.assertEqual([r['fuente'] for r in filtrados], [material['archivo']])
        fuera = self.raiz / 'fuera'
        fuera.mkdir()
        (fuera / 'secreto.md').write_text('confidencial centinela', encoding='utf-8')
        (academia.asignatura(curso, asignatura) / 'enlace').symlink_to(fuera, target_is_directory=True)
        self.assertEqual(nucleo.buscar_apuntes('centinela', boveda)['resultados'], [])

    def test_rechaza_escape_de_rutas_fechas_tipos_y_ids(self):
        for nombre in ('../fuera', 'C:\\datos', 'a/b', 'a\nb'):
            with self.assertRaises(ValueError):
                self.a.crear_asignatura(self.c, nombre)
        for cambio in ({'fecha': '2026-02-30'}, {'tipo': 'ejecutable'}):
            args = dict(curso=self.c, asignatura=self.s, tipo='tarea', titulo='Prueba', **{})
            args.update(cambio)
            with self.assertRaises(ValueError):
                self.a.anadir_material(**args)
        with self.assertRaises(ValueError):
            self.a.quitar_material(self.c, self.s, '../../fuera')

    def test_junction_o_enlace_no_permite_escritura_fuera(self):
        destino = self.raiz / 'fuera'
        destino.mkdir()
        enlace = self.a.asignatura(self.c, self.s) / 'tareas'
        enlace.rmdir()
        if os.name == 'nt':
            resultado = subprocess.run(['cmd.exe', '/c', 'mklink', '/J', str(enlace), str(destino)], capture_output=True)
            if resultado.returncode:
                self.skipTest('El equipo no permite crear la junction de prueba.')
        else:
            enlace.symlink_to(destino, target_is_directory=True)
        with self.assertRaises(ValueError):
            self.a.anadir_material(self.c, self.s, 'tarea', 'No salir')
        self.assertEqual(list(destino.iterdir()), [])

    def test_pdf_importado_original_conservado_y_texto_buscable(self):
        from pypdf import PdfWriter
        from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
        pdf = self.raiz / 'original.pdf'
        writer = PdfWriter()
        pagina = writer.add_blank_page(width=600, height=800)
        fuente = DictionaryObject({NameObject('/Type'): NameObject('/Font'), NameObject('/Subtype'): NameObject('/Type1'), NameObject('/BaseFont'): NameObject('/Helvetica')})
        pagina[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): writer._add_object(fuente)})})
        flujo = DecodedStreamObject()
        flujo.set_data(b'BT /F1 12 Tf 50 700 Td (Sensor farolillo diferencial P-101) Tj ET')
        pagina[NameObject('/Contents')] = writer._add_object(flujo)
        writer.write(pdf)
        original = pdf.read_bytes()
        m = self.a.anadir_material(self.c, self.s, 'apunte', 'PDF de sensores', archivo_origen=str(pdf))
        self.assertEqual(pdf.read_bytes(), original)
        self.assertEqual((self.raiz / m['adjunto']).read_bytes(), original)
        self.assertIn('Página 1', (self.raiz / m['archivo']).read_text(encoding='utf-8'))
        self.assertTrue(nucleo.buscar_apuntes('farolillo diferencial', self.raiz)['resultados'])


class MCPAcademico(unittest.IsolatedAsyncioTestCase):
    async def test_flujo_real_stdio_con_activacion_explicita(self):
        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as t:
            parametros = StdioServerParameters(command=sys.executable, args=[str(repo / 'integraciones/servidor_mcp.py'), '--boveda', t, '--gestion-academica'])
            async with Client(parametros, read_timeout_seconds=15) as cliente:
                catalogo = {h.name: h for h in (await cliente.list_tools()).tools}
                self.assertTrue(set(NOMBRES) <= set(catalogo))
                self.assertFalse(catalogo['crear_asignatura'].annotations.read_only_hint)
                self.assertTrue(catalogo['consultar_agenda'].annotations.read_only_hint)
                for herramienta, args in [
                    ('crear_curso', {'nombre': 'Tercero'}),
                    ('crear_asignatura', {'curso': 'Tercero', 'nombre': 'Control'}),
                    ('anadir_material', {'curso': 'Tercero', 'asignatura': 'Control', 'tipo': 'examen', 'titulo': 'Parcial', 'fecha': '2099-12-12', 'tema': '', 'contenido': ''}),
                    ('consultar_agenda', {}),
                    ('quitar_asignatura', {'curso': 'Tercero', 'asignatura': 'Control'}),
                    ('restaurar_asignatura', {'curso': 'Tercero', 'asignatura': 'Control'}),
                ]:
                    resultado = await cliente.call_tool(herramienta, args)
                    self.assertFalse(resultado.is_error, str(resultado.content))
                from pypdf import PdfWriter
                pdf = Path(t) / 'original.pdf'
                writer = PdfWriter()
                writer.add_blank_page(width=100, height=100)
                writer.write(pdf)
                resultado = await cliente.call_tool('importar_material', {
                    'curso': 'Tercero', 'asignatura': 'Control', 'tipo': 'apunte', 'titulo': 'PDF', 'archivo_origen': str(pdf)})
                self.assertFalse(resultado.is_error, str(resultado.content))
                self.assertTrue(pdf.is_file())
                fallo = await cliente.call_tool('actualizar_tarea', {'curso': 'Tercero', 'asignatura': 'Control', 'material_id': '../fuera', 'estado': 'completado'})
                self.assertTrue(fallo.is_error)
                self.assertIn('ID de material', str(fallo.content))
            self.assertIn('Parcial', (Path(t) / 'Carrera.md').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
