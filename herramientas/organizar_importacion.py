"""Vincula copias importadas con la carrera, sin mover adjuntos ni tocar originales."""
import hashlib
import json
import re
from pathlib import Path

from academia import Academia, INDICE_IMPORTACION, numero_curso, validar_nombre

MAX_TEXTO = 200_000


def organizar_pendientes(boveda):
    """Migra copias anteriores una vez, sin repetir la importación ni el escaneo."""
    if not Path(boveda).exists():
        return []
    gestor = Academia(boveda)
    base = gestor.ruta('apuntes', 'Importados')
    resultados = []
    if base.is_dir():
        for carpeta in sorted(base.iterdir()):
            gestor.ruta(gestor.relativa(carpeta))
            if carpeta.is_dir() and not carpeta.name.startswith('.') and not (carpeta / INDICE_IMPORTACION).exists():
                resultados.append(organizar(boveda, carpeta))
    gestor.panel()
    return resultados


def _contenido(gestor, raiz, archivo):
    if archivo.suffix.casefold() in ('.md', '.txt', '.csv'):
        with archivo.open('r', encoding='utf-8-sig', errors='replace') as entrada:
            return entrada.read(MAX_TEXTO)
    if archivo.suffix.casefold() == '.pdf':
        textos, longitud = [], 0
        relativa = archivo.relative_to(raiz)
        for derivado in sorted(raiz.glob('_Texto_consultable*')):
            gestor.ruta(gestor.relativa(derivado))
            if not derivado.is_dir():
                continue
            carpeta = gestor.ruta(gestor.relativa(derivado / relativa.parent))
            if not carpeta.is_dir():
                continue
            patron = re.compile(re.escape(archivo.name) + r'\.parte-(\d+)\.md$')
            notas = [(int(m[1]), p) for p in carpeta.iterdir() if (m := patron.fullmatch(p.name))]
            for _, nota in sorted(notas):
                gestor.ruta(gestor.relativa(nota))
                with nota.open('r', encoding='utf-8-sig', errors='replace') as entrada:
                    texto = entrada.read(MAX_TEXTO - longitud)
                textos.append(texto)
                longitud += len(texto)
                if longitud >= MAX_TEXTO:
                    break
            if textos:
                return '\n\n'.join(textos)[:MAX_TEXTO]
    return 'Texto no extraído. Consulta el adjunto original; no se ha aplicado OCR.'


def organizar(boveda, carpeta_importada):
    """Reconoce Curso 1..6/Primero..Sexto y sus asignaturas sin inventar el plan oficial.

    Cada documento se referencia desde una nota académica. Los IDs se conservan
    entre ejecuciones y una nota existente nunca se sobrescribe.
    """
    gestor = Academia(boveda)
    entrada = Path(carpeta_importada).absolute()
    # /var -> /private/var en macOS y nombres 8.3 en Windows pueden representar
    # la misma raíz con distinto texto. Conserva la ruta relativa antes de que
    # Academia la valide contra su raíz canónica; no resuelvas enlaces internos.
    for raiz_entrada in (Path(boveda).absolute(), gestor.raiz):
        try:
            relativa = entrada.relative_to(raiz_entrada)
            break
        except ValueError:
            continue
    else:
        raise ValueError('Solo se organizan copias dentro de apuntes/Importados.')
    if len(relativa.parts) != 3 or relativa.parts[:2] != ('apuntes', 'Importados'):
        raise ValueError('Elige una carpeta importada directamente dentro de apuntes/Importados.')
    raiz = gestor.ruta(relativa)
    if not raiz.is_dir() or raiz.name.startswith('.'):
        raise ValueError('No existe esa importación terminada.')
    indice = gestor.ruta(gestor.relativa(raiz / INDICE_IMPORTACION))
    if indice.exists():
        anterior = json.loads(indice.read_text(encoding='utf-8'))
        if anterior.get('formato') != 'ufv-organizacion-1':
            raise ValueError('El índice coincide con un archivo ajeno; no se sobrescribe.')
    # Valida todo el recorrido antes de crear metadatos.
    documentos = list(gestor.documentos(raiz))
    # La importación puede contener miles de archivos. Regenerar el panel por
    # cada asignatura vuelve a recorrer toda la biblioteca innecesariamente.
    gestor.panel = lambda: None
    cursos, asignaturas = {}, {}
    organizados = nuevos = existentes = 0
    for documento in documentos:
        partes = documento.relative_to(raiz).parts
        # Permite una carpeta envolvente (p. ej. Grado/Curso1), pero jamás
        # interpreta carpetas de temas/semestres como cursos por aproximación.
        posiciones = [i for i, nombre in enumerate(partes[:-2]) if numero_curso(nombre)]
        if not posiciones:
            continue
        posicion = posiciones[0]
        nombre_curso, nombre_asignatura = partes[posicion:posicion + 2]
        try:
            validar_nombre(nombre_asignatura)
        except ValueError:
            continue
        clave_curso = partes[:posicion + 1]
        if clave_curso not in cursos:
            datos = gestor.crear_curso(f'Curso {numero_curso(nombre_curso)}')
            cursos[clave_curso] = datos['id']
        curso = cursos[clave_curso]
        clave_asignatura = (curso, nombre_asignatura)
        if clave_asignatura not in asignaturas:
            datos = gestor.crear_asignatura(curso, nombre_asignatura)
            asignaturas[clave_asignatura] = datos['id']
        asignatura = asignaturas[clave_asignatura]
        identificador = hashlib.sha256(gestor.relativa(documento).encode('utf-8')).hexdigest()[:12]
        carpeta_asignatura = gestor.asignatura(curso, asignatura)
        nota = gestor.ruta(gestor.relativa(carpeta_asignatura / 'apuntes' / (identificador + '.md')))
        organizados += 1
        if nota.exists():
            existentes += 1
            continue
        adjunto = gestor.relativa(documento)
        titulo = documento.name[:120]
        datos = {'tipo': 'apunte', 'id': identificador, 'titulo': titulo, 'curso': curso,
                 'asignatura': asignatura, 'tema': '', 'fecha': '', 'estado': 'pendiente',
                 'origen_importado': gestor.relativa(raiz), 'adjunto': adjunto}
        contenido = f'# {titulo}\n\nAdjunto importado: [[{adjunto}]]\n\n' + _contenido(gestor, raiz, documento)
        gestor.escribir(nota, datos, contenido)
        nuevos += 1
    indice_notas = gestor.ruta('biblioteca', hashlib.sha256(gestor.relativa(raiz).encode()).hexdigest()[:12] + '.md')
    indice_notas.parent.mkdir(parents=True, exist_ok=True)
    lineas = [f'# Documentos de {raiz.name}', '', 'Índice generado de la copia importada. Los originales se conservan.', '']
    carpeta_anterior = None
    for documento in documentos:
        carpeta = documento.relative_to(raiz).parent.as_posix()
        if carpeta != carpeta_anterior:
            lineas += [f'## {carpeta}', '']
            carpeta_anterior = carpeta
        lineas.append(f'- [[{gestor.relativa(documento)}|{documento.name}]]')
    indice_notas.write_text('\n'.join(lineas) + '\n', encoding='utf-8')
    datos = {'formato': 'ufv-organizacion-1', 'documentos': len(documentos), 'indice': gestor.relativa(indice_notas),
             'organizados': organizados, 'sin_organizar': len(documentos) - organizados,
             'cursos': len(set(cursos.values())), 'asignaturas': len(asignaturas)}
    # Solo escribe el índice administrado; ninguna copia de documento se altera.
    indice.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding='utf-8')
    Academia.panel(gestor)
    return {**datos, 'notas_creadas': nuevos, 'notas_conservadas': existentes,
            'carpeta': gestor.relativa(raiz),
            'resumen': f'{organizados} documentos vinculados a {len(asignaturas)} asignaturas; '
                       f'{datos["sin_organizar"]} documentos disponibles en la biblioteca general.'}
