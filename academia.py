"""Organización académica local: Markdown de Obsidian y operaciones acotadas a la bóveda."""
import inspect
import json
import os
import re
import shutil
import stat
import tempfile
import unicodedata
import uuid
from typing import Literal
from datetime import date
from pathlib import Path

TIPOS = {'tema': 'temas', 'apunte': 'apuntes', 'tarea': 'tareas', 'examen': 'examenes'}
ESTADOS = ('pendiente', 'en_curso', 'completado')
DOCUMENTOS = {'.md', '.pdf', '.txt', '.csv', '.docx', '.pptx', '.xlsx', '.xls', '.png', '.jpg', '.jpeg', '.webp'}
INDICE_IMPORTACION = '_ufv_organizacion_academica.json'
LECTURA = {'listar_carrera', 'consultar_agenda'}
NOMBRES = ('listar_carrera', 'crear_curso', 'crear_asignatura', 'quitar_asignatura',
           'restaurar_asignatura', 'anadir_material', 'importar_material', 'actualizar_tarea', 'quitar_material', 'consultar_agenda')


def validar_nombre(valor, como_ruta=True):
    if not isinstance(valor, str) or not valor.strip() or len(valor) > 120:
        raise ValueError('Usa un nombre de entre 1 y 120 caracteres.')
    if (como_ruta and (any(c in valor for c in '/\\:[]|') or '..' in valor)) or any(ord(c) < 32 for c in valor):
        raise ValueError('El nombre no puede contener rutas ni caracteres de control.')
    return valor.strip()


def slug(valor, prefijo):
    valor = validar_nombre(valor)
    if valor.startswith(prefijo + '-'):
        return valor
    texto = unicodedata.normalize('NFKD', valor.lower()).encode('ascii', 'ignore').decode()
    texto = re.sub(r'[^a-z0-9]+', '-', texto).strip('-')
    if not texto:
        raise ValueError('El nombre necesita alguna letra o número.')
    return prefijo + '-' + texto[:90]


def numero_curso(nombre):
    """Reconoce solo nombres completos inequívocos; no deduce años académicos."""
    texto = unicodedata.normalize('NFKD', nombre.casefold()).encode('ascii', 'ignore').decode()
    texto = re.sub(r'[\s_-]+', '', texto)
    ordinales = {'primero': 1, 'segundo': 2, 'tercero': 3, 'cuarto': 4, 'quinto': 5, 'sexto': 6}
    if texto in ordinales:
        return ordinales[texto]
    coincidencia = re.fullmatch(r'(?:curso)?([1-6])(?:o)?(?:curso)?', texto)
    return int(coincidencia[1]) if coincidencia else None


def comprobar_fecha(valor):
    if not isinstance(valor, str):
        raise ValueError('La fecha debe ser texto AAAA-MM-DD o una cadena vacía.')
    if valor:
        if not isinstance(valor, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', valor):
            raise ValueError('La fecha debe ser AAAA-MM-DD.')
        date.fromisoformat(valor)
    return valor


class Academia:
    def __init__(self, boveda):
        self.raiz = Path(boveda).resolve()
        if not self.raiz.is_dir():
            raise ValueError('No existe la bóveda.')

    def ruta(self, *partes):
        p = self.raiz.joinpath(*partes)
        if self.raiz not in p.resolve().parents:
            raise ValueError('La operación debe permanecer dentro de la bóveda.')
        # Incluye junctions/reparse points de Windows, no solo enlaces POSIX.
        for componente in (p, *p.parents):
            if componente == self.raiz:
                break
            if componente.exists() or componente.is_symlink():
                s = componente.lstat()
                if stat.S_ISLNK(s.st_mode) or getattr(s, 'st_file_attributes', 0) & 0x400:
                    raise ValueError('No se permiten enlaces ni junctions en la estructura académica.')
        return p

    def relativa(self, p):
        return p.relative_to(self.raiz).as_posix()

    def leer(self, p):
        import yaml
        self.ruta(self.relativa(p))
        texto = p.read_text(encoding='utf-8-sig')
        lineas = texto.splitlines(keepends=True)
        if not lineas or lineas[0].strip() != '---':
            raise ValueError(f'Faltan propiedades en {self.relativa(p)}.')
        fin = next((i for i in range(1, len(lineas)) if lineas[i].strip() == '---'), None)
        if fin is None:
            raise ValueError('Falta el cierre de las propiedades Markdown.')
        datos = yaml.safe_load(''.join(lineas[1:fin]))
        if not isinstance(datos, dict):
            raise ValueError('Propiedades académicas no válidas.')
        datos = {k: v.isoformat() if isinstance(v, date) else v for k, v in datos.items()}
        return datos, ''.join(lineas[fin + 1:]).lstrip('\n')

    def escribir(self, p, datos, contenido):
        import yaml
        p = self.ruta(self.relativa(p))
        p.parent.mkdir(parents=True, exist_ok=True)
        texto = '---\n' + yaml.safe_dump(datos, allow_unicode=True, sort_keys=False) + '---\n\n' + contenido.rstrip() + '\n'
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=p.parent, delete=False, suffix='.tmp') as f:
            f.write(texto)
            temporal = Path(f.name)
        temporal.replace(p)

    def curso(self, curso):
        p = self.ruta('cursos', slug(curso, 'curso'))
        if not (p / 'Curso.md').is_file():
            numero = numero_curso(curso)
            candidatos = []
            if numero:
                for nota in self.ruta('cursos').glob('*/Curso.md'):
                    datos, _ = self.leer(nota)
                    if numero_curso(datos.get('nombre', '')) == numero:
                        candidatos.append(nota.parent)
            if len(candidatos) != 1:
                raise ValueError('No existe ese curso. Usa listar_carrera o crear_curso.')
            p = candidatos[0]
        self.ruta(self.relativa(p / 'Curso.md'))
        return p

    def asignatura(self, curso, asignatura):
        p = self.curso(curso) / 'asignaturas' / slug(asignatura, 'asignatura')
        self.ruta(self.relativa(p))
        if not (p / 'Asignatura.md').is_file():
            raise ValueError('No existe esa asignatura en ese curso. Usa listar_carrera.')
        return p

    def materiales(self, p):
        resultado = []
        for tipo, carpeta in TIPOS.items():
            base = self.ruta(self.relativa(p / carpeta))
            if not base.is_dir():
                continue
            for f in sorted(base.glob('*.md')):
                datos, _ = self.leer(f)
                resultado.append(dict(datos, archivo=self.relativa(f)))
        return resultado

    def listar_carrera(self, curso: str = '', asignatura: str = '', limite: int = 25, desplazamiento: int = 0) -> dict:
        """Lista cursos y asignaturas con recuentos. Con curso y asignatura devuelve materiales e IDs, 25 por página. Si hay_mas, repite con siguiente_desplazamiento. limite: 1..50."""
        if type(limite) is not int or not 1 <= limite <= 50 or type(desplazamiento) is not int or desplazamiento < 0:
            raise ValueError('Usa limite entero entre 1 y 50 y desplazamiento entero no negativo.')
        if asignatura and not curso:
            raise ValueError('Indica el curso de esa asignatura.')
        base = self.ruta('cursos')
        cursos = [self.curso(curso)] if curso else sorted(base.glob('*/Curso.md')) if base.exists() else []
        resultado = []
        for item in cursos:
            p = item if item.is_dir() else item.parent
            datos, _ = self.leer(p / 'Curso.md')
            asignaturas = []
            candidatos = [self.asignatura(curso, asignatura)] if asignatura else sorted((p / 'asignaturas').glob('*/Asignatura.md'))
            for a in candidatos:
                a = a if a.is_dir() else a.parent
                meta, _ = self.leer(a / 'Asignatura.md')
                resumen = {tipo: sum(1 for _ in self.ruta(self.relativa(a / carpeta)).glob('*.md'))
                           for tipo, carpeta in TIPOS.items()}
                detalle = {}
                if asignatura:
                    materiales = self.materiales(a)
                    pagina = materiales[desplazamiento:desplazamiento + limite]
                    # El listado transmite metadatos útiles; el contenido se busca aparte.
                    pagina = [{k: v for k, v in m.items() if k in ('id', 'tipo', 'titulo', 'tema', 'fecha', 'estado', 'archivo', 'adjunto')} for m in pagina]
                    siguiente = desplazamiento + len(pagina)
                    detalle = {'materiales': pagina, 'total_materiales': len(materiales),
                               'hay_mas': siguiente < len(materiales),
                               'siguiente_desplazamiento': siguiente if siguiente < len(materiales) else None}
                asignaturas.append(dict(meta, archivo=self.relativa(a / 'Asignatura.md'),
                                         resumen_materiales=resumen, materiales_incluidos=bool(asignatura), **detalle))
            resultado.append(dict(datos, asignaturas=asignaturas))
        biblioteca = self.biblioteca() if not curso else {'nota': 'La biblioteca general está en listar_carrera sin filtros.'}
        return {'cursos': resultado, 'panel': 'Carrera.md', 'biblioteca': biblioteca,
                'memoria': {'ruta': 'memoria', 'uso': 'Contexto y preferencias del alumno. Los documentos están en la biblioteca y las asignaturas.'}}

    def biblioteca(self):
        """Resumen compacto de documentos generales e importaciones pendientes de clasificar."""
        importaciones = []
        base = self.ruta('apuntes', 'Importados')
        if base.exists():
            for carpeta in sorted(base.iterdir()):
                self.ruta(self.relativa(carpeta))
                if not carpeta.is_dir() or carpeta.name.startswith('.'):
                    continue
                indice = self.ruta(self.relativa(carpeta / INDICE_IMPORTACION))
                if indice.is_file():
                    datos = json.loads(indice.read_text(encoding='utf-8'))
                    if datos.get('formato') != 'ufv-organizacion-1':
                        raise ValueError('Índice de importación desconocido.')
                    importaciones.append({'ruta': self.relativa(carpeta), 'documentos': datos['documentos'],
                                          'organizados': datos['organizados'], 'sin_organizar': datos['sin_organizar'],
                                          'indice': self.relativa(self.ruta(datos['indice'])) if datos.get('indice') else ''})
                else:
                    cantidad = sum(1 for _ in self.documentos(carpeta))
                    importaciones.append({'ruta': self.relativa(carpeta), 'documentos': cantidad,
                                          'organizados': 0, 'sin_organizar': cantidad})
        generales = self.ruta('apuntes')
        cantidad = sum(1 for _ in self.documentos(generales, excluir={'Importados'})) if generales.exists() else 0
        return {'importaciones': importaciones, 'apuntes_generales': {'ruta': 'apuntes', 'documentos': cantidad},
                'sin_organizar': cantidad + sum(i['sin_organizar'] for i in importaciones),
                'nota': 'Los documentos sin organizar se pueden buscar sin filtro de curso. No implican asignaturas oficiales.'}

    def documentos(self, carpeta, excluir=()):
        """Recorre documentos sin seguir enlaces, junctions, cachés ni texto derivado."""
        omitidos = {'.git', '.obsidian', '.venv', 'node_modules', '__pycache__', '.tools', '.local', *excluir}
        for actual, directorios, archivos in os.walk(carpeta, followlinks=False):
            for nombre in list(directorios):
                if nombre.startswith('.') or nombre in omitidos or nombre.startswith('_Texto_consultable'):
                    directorios.remove(nombre)
                else:
                    self.ruta(self.relativa(Path(actual) / nombre))
            for nombre in sorted(archivos):
                archivo = Path(actual) / nombre
                if nombre.startswith('.') or archivo.suffix.casefold() not in DOCUMENTOS:
                    continue
                yield self.ruta(self.relativa(archivo))

    def crear_curso(self, nombre: str) -> dict:
        """Crea un curso, por ejemplo '2026-2027 tercero'. Devuelve su ID. No inventa asignaturas del plan de estudios."""
        titulo = validar_nombre(nombre)
        p = self.ruta('cursos', slug(titulo, 'curso'), 'Curso.md')
        if p.exists():
            datos, _ = self.leer(p)
            return dict(datos, creado=False, archivo=self.relativa(p))
        datos = {'tipo': 'curso', 'id': p.parent.name, 'nombre': titulo}
        self.escribir(p, datos, f'# {titulo}\n\nAsigna tus asignaturas a este curso desde el tutor.\n')
        self.panel()
        return dict(datos, creado=True, archivo=self.relativa(p))

    def crear_asignatura(self, curso: str, nombre: str) -> dict:
        """Crea una asignatura dentro de un curso existente, con carpetas para temas, apuntes, tareas, exámenes y adjuntos."""
        titulo = validar_nombre(nombre)
        p = self.ruta(self.relativa(self.curso(curso)), 'asignaturas', slug(titulo, 'asignatura'))
        nota = p / 'Asignatura.md'
        if nota.exists():
            datos, _ = self.leer(nota)
            return dict(datos, creada=False, archivo=self.relativa(nota))
        datos = {'tipo': 'asignatura', 'id': p.name, 'nombre': titulo, 'curso': p.parent.parent.name}
        self.escribir(nota, datos, f'# {titulo}\n\nOrganiza aquí tus temas, apuntes, tareas y exámenes.\n')
        for carpeta in (*TIPOS.values(), 'adjuntos'):
            self.ruta(self.relativa(p / carpeta)).mkdir(exist_ok=True)
        self.panel()
        return dict(datos, creada=True, archivo=self.relativa(nota))

    def quitar_asignatura(self, curso: str, asignatura: str) -> dict:
        """Quita una asignatura del curso moviéndola entera a la papelera de la bóveda. Conserva sus materiales y permite restaurarla."""
        origen = self.asignatura(curso, asignatura)
        destino = self.ruta('papelera', 'asignaturas', uuid.uuid4().hex, origen.name)
        # Ambos destinos absolutos se validan antes del movimiento recursivo.
        self.ruta(self.relativa(origen)); self.ruta(self.relativa(destino))
        destino.parent.mkdir(parents=True)
        shutil.move(str(origen), str(destino))
        self.panel()
        return {'quitada': True, 'borrado_definitivo': False, 'papelera': self.relativa(destino), 'restaurar_con': 'restaurar_asignatura'}

    def restaurar_asignatura(self, curso: str, asignatura: str) -> dict:
        """Recupera de la papelera una asignatura del curso indicado. Rechaza sobrescribir una asignatura activa."""
        c = self.curso(curso)
        sid = slug(asignatura, 'asignatura')
        candidatos = []
        for f in self.ruta('papelera', 'asignaturas').glob(f'*/{sid}/Asignatura.md'):
            datos, _ = self.leer(f)
            if datos.get('curso') == c.name:
                candidatos.append(f.parent)
        if len(candidatos) != 1:
            raise ValueError('No hay una única copia archivada. Revisa la papelera de Obsidian.')
        destino = self.ruta(self.relativa(c), 'asignaturas', sid)
        if destino.exists():
            raise ValueError('Ya existe una asignatura activa con ese nombre; no se sobrescribe.')
        origen = self.ruta(self.relativa(candidatos[0]))
        destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(origen), str(destino))
        self.panel()
        return {'restaurada': True, 'archivo': self.relativa(destino / 'Asignatura.md')}

    def anadir_material(self, curso: str, asignatura: str, tipo: Literal['tema', 'apunte', 'tarea', 'examen'], titulo: str,
                        contenido: str = '', tema: str = '', fecha: str = '', archivo_origen: str = '') -> dict:
        """Añade tema, apunte, tarea o examen a una asignatura con contenido, tema y fecha AAAA-MM-DD. Para adjuntar un archivo usa importar_material."""
        if tipo not in TIPOS:
            raise ValueError('Tipo: tema, apunte, tarea o examen.')
        titulo = validar_nombre(titulo, como_ruta=False)
        if not isinstance(contenido, str) or len(contenido) > 100000:
            raise ValueError('El contenido debe tener como máximo 100000 caracteres.')
        if tema:
            tema = validar_nombre(tema, como_ruta=False)
        comprobar_fecha(fecha)
        a = self.asignatura(curso, asignatura)
        identificador = uuid.uuid4().hex[:12]
        nota = self.ruta(self.relativa(a), TIPOS[tipo], identificador + '.md')
        datos = {'tipo': tipo, 'id': identificador, 'titulo': titulo, 'curso': a.parent.parent.name,
                 'asignatura': a.name, 'tema': tema, 'fecha': fecha, 'estado': 'pendiente'}
        texto = f'# {titulo}\n\n' + contenido
        aviso = ''
        if archivo_origen:
            origen = Path(archivo_origen).expanduser().resolve()
            if not origen.is_file() or origen.stat().st_size > 32 * 1024**2:
                raise ValueError('El adjunto debe ser un archivo local de hasta 32 MB.')
            extension = origen.suffix.lower()
            if extension not in ('.pdf', '.md', '.txt', '.csv', '.png', '.jpg', '.jpeg', '.docx', '.pptx'):
                raise ValueError('Formato de adjunto no admitido.')
            extraido = ''
            if extension == '.pdf':
                from pypdf import PdfReader
                lector = PdfReader(origen)
                if lector.is_encrypted:
                    raise ValueError('El PDF está cifrado; proporciona una copia sin contraseña.')
                paginas = []
                total = 0
                for i, pagina in enumerate(lector.pages[:100], 1):
                    t = (pagina.extract_text() or '')[:15000]
                    total += len(t)
                    paginas.append(f'## Página {i}\n\n{t}')
                    if total >= 200000:
                        aviso = 'Texto limitado a 200000 caracteres.'
                        break
                extraido = '\n\n'.join(paginas)
                if not any((p.extract_text() or '').strip() for p in lector.pages[:1]):
                    aviso = 'Puede ser un PDF escaneado: no se aplica OCR. Solo se indexan las páginas con texto.'
                if len(lector.pages) > 100:
                    aviso = 'Solo se han extraído las primeras 100 páginas.'
            elif extension in ('.md', '.txt', '.csv'):
                extraido = origen.read_text(encoding='utf-8-sig')[:200000]
            adjunto = self.ruta(self.relativa(a), 'adjuntos', identificador + extension)
            adjunto.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(origen, adjunto)
            datos['adjunto'] = self.relativa(adjunto)
            texto += f'\n\nArchivo original: [[{datos["adjunto"]}]]\n\n' + extraido
        if aviso:
            texto += '\n\nAviso de importación: ' + aviso
        self.escribir(nota, datos, texto)
        self.panel()
        return dict(datos, archivo=self.relativa(nota), guardado=True, aviso=aviso)

    def material(self, curso, asignatura, material_id):
        if not re.fullmatch(r'[a-f0-9]{12}', material_id):
            raise ValueError('Usa el ID de material devuelto por listar_carrera.')
        a = self.asignatura(curso, asignatura)
        for carpeta in TIPOS.values():
            p = self.ruta(self.relativa(a), carpeta, material_id + '.md')
            if p.is_file():
                return p
        raise ValueError('No existe ese material en esa asignatura.')

    def importar_material(self, curso: str, asignatura: str, tipo: Literal['tema', 'apunte', 'tarea', 'examen'], titulo: str, archivo_origen: str,
                          tema: str = '', contenido: str = '', fecha: str = '') -> dict:
        """Importa un archivo local indicado por el alumno como material de una asignatura. Copia el original y extrae texto de PDF, MD, TXT o CSV."""
        if not archivo_origen:
            raise ValueError('Indica la ruta del archivo que quieres importar.')
        return self.anadir_material(curso, asignatura, tipo, titulo, contenido, tema, fecha, archivo_origen)

    def actualizar_tarea(self, curso: str, asignatura: str, material_id: str, estado: Literal['pendiente', 'en_curso', 'completado'], fecha: str = '') -> dict:
        """Actualiza estado (pendiente, en_curso o completado) y opcionalmente fecha de una tarea o examen usando su ID."""
        if estado not in ESTADOS:
            raise ValueError('Estado: pendiente, en_curso o completado.')
        comprobar_fecha(fecha)
        p = self.material(curso, asignatura, material_id)
        datos, texto = self.leer(p)
        if datos['tipo'] not in ('tarea', 'examen'):
            raise ValueError('Solo se actualiza el estado de tareas o exámenes.')
        datos['estado'] = estado
        if fecha:
            datos['fecha'] = fecha
        self.escribir(p, datos, texto)
        self.panel()
        return dict(datos, actualizado=True, archivo=self.relativa(p))

    def quitar_material(self, curso: str, asignatura: str, material_id: str) -> dict:
        """Retira un material de una asignatura moviendo su nota a papelera. Conserva el adjunto original."""
        origen = self.material(curso, asignatura, material_id)
        destino = self.ruta('papelera', 'materiales', uuid.uuid4().hex + '.md')
        destino.parent.mkdir(parents=True, exist_ok=True)
        origen.rename(destino)
        self.panel()
        return {'quitado': True, 'borrado_definitivo': False, 'papelera': self.relativa(destino)}

    def consultar_agenda(self, curso: str = '', asignatura: str = '') -> dict:
        """Lista tareas y exámenes pendientes por fecha, indica vencidos y permite filtrar por curso y asignatura."""
        filas = []
        carrera = self.listar_carrera(curso, asignatura)
        for c in carrera['cursos']:
            for a in c['asignaturas']:
                materiales = a['materiales'] if asignatura else self.materiales(self.asignatura(c['id'], a['id']))
                for m in materiales:
                    if m['tipo'] in ('tarea', 'examen') and m.get('estado') != 'completado':
                        fecha = str(m.get('fecha') or '')
                        filas.append(dict(m, fecha=fecha, vencido=bool(fecha and fecha < date.today().isoformat())))
        return {'hoy': date.today().isoformat(), 'pendientes': sorted(filas, key=lambda m: (not bool(m['fecha']), m['fecha'], m['titulo']))[:200]}

    def panel(self):
        carrera = self.listar_carrera()
        lineas = ['# Mi carrera', '', 'Cursos, asignaturas, temas, tareas y exámenes compartidos con el tutor.', '',
                  'Pide: «Crea el curso 2026-2027 tercero y la asignatura Automatización».',
                  'Después: «Añade el tema Sensores», «Añade la práctica de sensores para el 30 de noviembre» o «¿Qué tengo pendiente?».', '',
                  'Quitar una asignatura la lleva a la papelera; se puede restaurar desde el chat.', '']
        for c in carrera['cursos']:
            lineas += [f'## {c["nombre"]}', '']
            for a in c['asignaturas']:
                lineas.append(f'- [[{a["archivo"]}|{a["nombre"]}]]')
                for m in self.materiales(self.asignatura(c['id'], a['id'])):
                    lineas.append(f'  - {m["tipo"]}: [[{m["archivo"]}|{m["titulo"]}]] · {m.get("estado", "")} · {m.get("fecha") or "sin fecha"}')
            lineas.append('')
        lineas += ['## Biblioteca y documentos sin organizar', '',
                   'Los documentos importados pertenecen a la misma bóveda. Los que no tienen curso reconocido siguen disponibles mediante búsqueda general.', '']
        biblioteca = carrera['biblioteca']
        for entrada in biblioteca['importaciones']:
            destino = entrada.get('indice')
            enlace = f'[[{destino}|{Path(entrada["ruta"]).name}]]' if destino else f'`{entrada["ruta"]}`'
            lineas.append(f'- {enlace}: {entrada["documentos"]} documentos; {entrada["organizados"]} vinculados a asignaturas; {entrada["sin_organizar"]} pendientes de organizar.')
        lineas += [f'- Apuntes generales en `apuntes/`: {biblioteca["apuntes_generales"]["documentos"]} documentos.', '',
                   '## Memoria', '', '`memoria/`: contexto y preferencias del alumno. Los apuntes permanecen en la biblioteca y las asignaturas.', '']
        self.ruta('Carrera.md').write_text('\n'.join(lineas), encoding='utf-8')


def especificaciones():
    resultado = []
    for n in NOMBRES:
        funcion = getattr(Academia, n)
        propiedades, requeridos = {}, []
        for p in inspect.signature(funcion).parameters.values():
            if p.name == 'self':
                continue
            propiedades[p.name] = {'type': 'integer' if p.annotation is int else 'string'}
            if p.name == 'tipo':
                propiedades[p.name]['enum'] = list(TIPOS)
            if p.name == 'estado':
                propiedades[p.name]['enum'] = list(ESTADOS)
            if p.default is inspect.Parameter.empty:
                requeridos.append(p.name)
        if n == 'anadir_material':
            propiedades.pop('archivo_origen')
            requeridos.append('tema')
        resultado.append({'type': 'function', 'function': {'name': n, 'description': inspect.getdoc(funcion),
            'parameters': {'type': 'object', 'properties': propiedades, 'required': requeridos, 'additionalProperties': False}}})
    return resultado
