import hashlib
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from academia import Academia
from herramientas.organizar_importacion import organizar, organizar_pendientes
import nucleo


class OrganizarImportacion(unittest.TestCase):
    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)
        self.base = Path(self.temporal.name).resolve()
        self.boveda = self.base / 'boveda'
        self.importacion = self.boveda / 'apuntes' / 'Importados' / 'Universidad-123'
        self.importacion.mkdir(parents=True)
        self.gestor = Academia(self.boveda)

    def archivo(self, nombre, contenido):
        archivo = self.importacion / nombre
        archivo.parent.mkdir(parents=True, exist_ok=True)
        archivo.write_text(contenido, encoding='utf-8')
        return archivo

    def test_cursos_materiales_busqueda_pdf_referencias_e_idempotencia(self):
        archivos = [self.archivo('Curso1/Automatización/Prácticas/apunte.md', 'MQTT sensor P101'),
                    self.archivo('Curso1/Automatización/sensores.pdf', 'PDF fixture original'),
                    self.archivo('Segundo/Control/control.txt', 'control PID'),
                    self.archivo('Segundo/Control/clase.docx', 'binario conservado')]
        hashes = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in archivos}
        self.archivo('_Texto_consultable/Curso1/Automatización/sensores.pdf.parte-1.md', 'P101 transductor manométrico')
        self.archivo('_Texto_consultable/Curso1/Automatización/sensores.pdf.parte-2.md', 'P102 transductor diferencial')
        resultado = organizar(self.boveda, self.importacion)
        self.assertEqual(resultado['notas_creadas'], 4)
        self.assertEqual(resultado['asignaturas'], 2)
        indice = self.boveda / resultado['indice']
        self.assertTrue(indice.is_file())
        self.assertIn('[[apuntes/Importados/Universidad-123/Curso1/', indice.read_text(encoding='utf-8'))
        listado = self.gestor.listar_carrera('primero', 'Automatización')
        materiales = listado['cursos'][0]['asignaturas'][0]['materiales']
        self.assertEqual(len(materiales), 2)
        pdf = next(m for m in materiales if m['titulo'].endswith('.pdf'))
        _, contenido = self.gestor.leer(self.boveda / pdf['archivo'])
        self.assertIn('P101 transductor manométrico', contenido)
        self.assertIn('P102 transductor diferencial', contenido)
        self.assertEqual(pdf['adjunto'], self.gestor.relativa(archivos[1]))
        self.assertTrue(nucleo.buscar_apuntes('P101', self.boveda, curso='Curso1', asignatura='Automatización')['resultados'])
        self.assertFalse(nucleo.buscar_apuntes('P101', self.boveda, curso='Segundo', asignatura='Control')['resultados'])
        nota = self.boveda / pdf['archivo']
        nota.write_text(nota.read_text(encoding='utf-8') + '\nEdición del alumno\n', encoding='utf-8')
        repetido = organizar(self.boveda, self.importacion)
        self.assertEqual(repetido['notas_creadas'], 0)
        self.assertEqual(repetido['notas_conservadas'], 4)
        self.assertIn('Edición del alumno', nota.read_text(encoding='utf-8'))
        self.assertEqual(hashes, {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in archivos})
        self.assertEqual(len(list(self.importacion.rglob('sensores.pdf'))), 1)

    def test_biblioteca_general_visible_sin_inventar_cursos(self):
        self.archivo('Ideas generales/plan.md', 'Preferencias del proyecto')
        self.archivo('Curso desconocido/Robótica/nota.txt', 'PWM')
        self.archivo('binarios/programa.exe', 'ejecutable')
        self.archivo('CAD/modelo.step', 'geometría')
        (self.boveda / 'apuntes' / 'libre.md').write_text('nota libre', encoding='utf-8')
        antes = self.gestor.listar_carrera()
        self.assertEqual(antes['biblioteca']['sin_organizar'], 3)
        resultado = organizar(self.boveda, self.importacion)
        self.assertEqual(resultado['sin_organizar'], 2)
        carrera = self.gestor.listar_carrera()
        self.assertEqual(carrera['cursos'], [])
        self.assertEqual(carrera['biblioteca']['sin_organizar'], 3)
        self.assertIn('pendientes de organizar', (self.boveda / 'Carrera.md').read_text(encoding='utf-8'))
        self.assertIn('Memoria', (self.boveda / 'Carrera.md').read_text(encoding='utf-8'))

    def test_no_acepta_originales_fuera_de_la_copia(self):
        originales = self.base / 'originales'
        originales.mkdir()
        with self.assertRaises(ValueError):
            organizar(self.boveda, originales)
        self.assertEqual(list(originales.iterdir()), [])

    def test_acepta_la_raiz_original_antes_de_normalizar_alias_del_sistema(self):
        self.archivo('Curso 2/Control/presion.md', 'P77')
        entrada = Path(self.temporal.name) / 'boveda'
        resultado = organizar(entrada, entrada / 'apuntes/Importados/Universidad-123')
        self.assertEqual(resultado['notas_creadas'], 1)
        self.assertEqual(len(self.gestor.listar_carrera('segundo', 'Control')['cursos'][0]['asignaturas'][0]['materiales']), 1)

    def test_alumno_importa_y_consulta_sin_organizacion_manual(self):
        from herramientas.importar_carpeta import importar
        originales = self.base / 'mis-notas'
        nota = originales / 'Curso 2' / 'Control' / 'bomba.md'
        nota.parent.mkdir(parents=True)
        nota.write_text('La bomba P101 trabaja a 3.2 bar.', encoding='utf-8')
        resultado = importar(originales, self.boveda)
        self.assertEqual(resultado['organizacion']['notas_creadas'], 1)
        lista = self.gestor.listar_carrera('segundo', 'Control')
        self.assertEqual(len(lista['cursos'][0]['asignaturas'][0]['materiales']), 1)
        self.assertTrue(nucleo.buscar_apuntes('P101', self.boveda, curso='segundo', asignatura='Control')['resultados'])
        self.assertEqual(nota.read_text(encoding='utf-8'), 'La bomba P101 trabaja a 3.2 bar.')

    def test_arranque_migra_importacion_antigua_una_sola_vez(self):
        self.archivo('Curso 3/Robotica/nota.md', 'Robot R42')
        self.assertEqual(len(organizar_pendientes(self.boveda)), 1)
        self.assertEqual(organizar_pendientes(self.boveda), [])
        self.assertEqual(len(self.gestor.listar_carrera('tercero', 'Robotica')['cursos'][0]['asignaturas'][0]['materiales']), 1)

    def test_materiales_grandes_se_paginan_sin_ocultarlos(self):
        for i in range(53):
            self.archivo(f'Curso 2/Control/documento-{i}.txt', f'Contenido {i}')
        organizar(self.boveda, self.importacion)
        recibidos, siguiente = set(), 0
        while True:
            materia = self.gestor.listar_carrera('segundo', 'Control', limite=20, desplazamiento=siguiente)['cursos'][0]['asignaturas'][0]
            self.assertEqual(materia['total_materiales'], 53)
            self.assertLessEqual(len(materia['materiales']), 20)
            recibidos.update(m['id'] for m in materia['materiales'])
            if not materia['hay_mas']:
                break
            siguiente = materia['siguiente_desplazamiento']
        self.assertEqual(len(recibidos), 53)

    def test_pdf_con_corchetes_reutiliza_derivado_y_limita_texto(self):
        self.archivo('Curso 4/Control/sensor [1].pdf', 'PDF')
        self.archivo('_Texto_consultable/Curso 4/Control/sensor [1].pdf.parte-1.md', 'P101 ' + 'x' * 210000)
        organizar(self.boveda, self.importacion)
        materiales = self.gestor.listar_carrera('cuarto', 'Control')['cursos'][0]['asignaturas'][0]['materiales']
        _, contenido = self.gestor.leer(self.boveda / materiales[0]['archivo'])
        self.assertIn('P101', contenido)
        self.assertLess(len(contenido), 201000)

    def test_alias_no_confunde_cursos_anuales_y_prioriza_exacto(self):
        self.gestor.crear_curso('2025-2026 tercero')
        self.gestor.crear_curso('2026-2027 tercero')
        with self.assertRaises(ValueError):
            self.gestor.curso('tercero')
        self.gestor.crear_curso('Curso 3')
        self.assertEqual(self.gestor.curso('tercero').name, 'curso-curso-3')
        self.gestor.crear_curso('Tercero')
        self.assertEqual(self.gestor.curso('tercero').name, 'curso-tercero')
        with self.assertRaises(ValueError):
            self.gestor.curso('curso3')

    def test_rechaza_junction_o_enlace_sin_escribir_notas(self):
        fuera = self.base / 'fuera'
        fuera.mkdir()
        (fuera / 'secreto.md').write_text('secreto', encoding='utf-8')
        enlace = self.importacion / 'Curso1'
        if os.name == 'nt':
            proceso = subprocess.run(['cmd', '/c', 'mklink', '/J', str(enlace), str(fuera)], capture_output=True)
            if proceso.returncode:
                self.skipTest('No se pueden crear junctions.')
            self.addCleanup(lambda: os.rmdir(enlace) if enlace.exists() else None)
        else:
            enlace.symlink_to(fuera, target_is_directory=True)
        with self.assertRaises(ValueError):
            organizar(self.boveda, self.importacion)
        self.assertFalse((self.boveda / 'cursos').exists())
        self.assertEqual((fuera / 'secreto.md').read_text(encoding='utf-8'), 'secreto')


if __name__ == '__main__':
    unittest.main()
