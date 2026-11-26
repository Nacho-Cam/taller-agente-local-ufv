"""Importa documentos a una copia independiente; nunca modifica la carpeta original."""
import argparse
import json
import os
import re
import shutil
import stat
import uuid
from pathlib import Path

EXCLUIDOS = {'.git', '.obsidian', '.venv', 'venv', 'node_modules', '.tools', '.local', '__pycache__'}
MAX_TEXTO = 200_000


def _enlace(ruta):
    datos = ruta.lstat()
    return stat.S_ISLNK(datos.st_mode) or bool(getattr(datos, 'st_file_attributes', 0) & 0x400)


def _rutas(origen, boveda):
    origen, boveda = Path(origen).expanduser().absolute(), Path(boveda).expanduser().absolute()
    if not origen.is_dir() or _enlace(origen):
        raise ValueError('Elige una carpeta de documentos existente, sin enlaces.')
    # Canonicaliza ancestros externos (por ejemplo /var en macOS). Los enlaces
    # de la propia bóveda y de sus carpetas internas sí se rechazan.
    if boveda.exists() and _enlace(boveda):
        raise ValueError('La bóveda no puede ser un enlace o junction.')
    origen, boveda = origen.resolve(), boveda.resolve()
    hogar = Path.home().resolve()
    if origen == Path(origen.anchor) or origen == hogar or origen in hogar.parents:
        raise ValueError('Elige la carpeta de universidad, no todo el disco ni tu carpeta personal.')
    if origen == boveda or origen in boveda.parents or boveda in origen.parents:
        raise ValueError('La carpeta original y la bóveda deben estar separadas, sin contenerse una a otra.')
    return origen, boveda


def analizar(origen, boveda):
    """Devuelve conteos, bytes, archivos relativos y omitidos sin crear ni modificar nada."""
    origen, boveda = _rutas(origen, boveda)
    archivos, omitidos = [], []

    def recorrer(carpeta):
        with os.scandir(carpeta) as entradas:
            for entrada in sorted(entradas, key=lambda e: e.name.casefold()):
                ruta = Path(entrada.path)
                relativa = ruta.relative_to(origen).as_posix()
                if entrada.name.startswith('.') or entrada.name.casefold() in EXCLUIDOS:
                    omitidos.append({'archivo': relativa, 'motivo': 'carpeta o archivo de configuración/oculto'})
                    continue
                if _enlace(ruta):
                    omitidos.append({'archivo': relativa, 'motivo': 'enlace o junction'})
                    continue
                datos = ruta.stat(follow_symlinks=False)
                if getattr(datos, 'st_file_attributes', 0) & 0x2:
                    omitidos.append({'archivo': relativa, 'motivo': 'archivo o carpeta ocultos'})
                    continue
                if stat.S_ISDIR(datos.st_mode):
                    recorrer(ruta)
                elif stat.S_ISREG(datos.st_mode):
                    archivos.append({'archivo': relativa, 'bytes': datos.st_size})
                else:
                    omitidos.append({'archivo': relativa, 'motivo': 'no es un archivo normal'})

    recorrer(origen)
    total = sum(a['bytes'] for a in archivos)
    derivaciones = sum(Path(a['archivo']).suffix.lower() in ('.pdf', '.txt', '.csv') for a in archivos)
    necesarios = total + derivaciones * 1024**2 + max(64 * 1024**2, total // 10)
    return {'origen': str(origen), 'boveda': str(boveda), 'archivos': archivos,
            'total_archivos': len(archivos), 'bytes': total, 'bytes_necesarios': necesarios,
            'omitidos': omitidos,
            'resumen': f'{len(archivos)} archivos, {total / 1024**2:.1f} MB; {len(omitidos)} entradas omitidas. Se copiarán sin modificar los originales.'}


def _copiar(origen, destino):
    if _enlace(origen):
        raise ValueError('La carpeta cambió durante la importación: apareció un enlace.')
    antes = origen.stat()
    descriptor = os.open(origen, os.O_RDONLY | getattr(os, 'O_BINARY', 0) | getattr(os, 'O_NOFOLLOW', 0))
    with os.fdopen(descriptor, 'rb') as entrada:
        abierto = os.fstat(entrada.fileno())
        if not stat.S_ISREG(abierto.st_mode) or (antes.st_dev, antes.st_ino) != (abierto.st_dev, abierto.st_ino):
            raise ValueError('Un archivo cambió durante la importación. Inténtalo de nuevo.')
        destino.parent.mkdir(parents=True, exist_ok=True)
        with destino.open('xb') as salida:
            shutil.copyfileobj(entrada, salida, length=1024 * 1024)
        despues = os.fstat(entrada.fileno())
        if (abierto.st_size, abierto.st_mtime_ns) != (despues.st_size, despues.st_mtime_ns):
            raise ValueError('Un archivo cambió durante la importación. Inténtalo de nuevo.')
    os.utime(destino, ns=(antes.st_atime_ns, antes.st_mtime_ns))


def _extraer(archivo):
    """Extrae texto acotado de la COPIA, nunca del original; sin OCR ni red."""
    if archivo.suffix.lower() == '.pdf':
        from pypdf import PdfReader
        lector = PdfReader(archivo)
        if lector.is_encrypted:
            raise ValueError('PDF cifrado: no se ha extraído texto.')
        textos, cantidad = [], 0
        for numero, pagina in enumerate(lector.pages[:100], 1):
            texto = (pagina.extract_text() or '')[:min(15000, MAX_TEXTO - cantidad)]
            if texto.strip():
                textos.append(f'## Página {numero}\n\n{texto}')
                cantidad += len(texto)
            if cantidad >= MAX_TEXTO:
                break
        limitado = len(lector.pages) > 100 or cantidad >= MAX_TEXTO
        return '\n\n'.join(textos), limitado
    with archivo.open('r', encoding='utf-8-sig', errors='replace') as entrada:
        texto = entrada.read(MAX_TEXTO + 1)
    return texto[:MAX_TEXTO], len(texto) > MAX_TEXTO


def importar(origen, boveda, progreso=None):
    """Copia atómica a apuntes/Importados/nombre-UUID; progreso recibe un str por archivo.

    El resultado contiene destino, conteos, PDFs sin texto, errores de extracción y resumen.
    Los errores de lectura/copia abortan todo; los de extracción conservan el adjunto.
    """
    plan = analizar(origen, boveda)
    if not plan['total_archivos']:
        raise ValueError('La carpeta no contiene archivos importables.')
    origen, boveda = Path(plan['origen']), Path(plan['boveda'])
    existente = boveda
    while not existente.exists():
        existente = existente.parent
    if shutil.disk_usage(existente).free < plan['bytes_necesarios']:
        raise ValueError(f'No hay espacio suficiente: se necesitan {plan["bytes_necesarios"] / 1024**2:.0f} MB libres, incluido el margen.')
    raiz = boveda / 'apuntes' / 'Importados'
    for parte in (boveda / 'apuntes', raiz):
        if parte.exists() and _enlace(parte):
            raise ValueError('El destino de importación contiene un enlace o junction.')
    raiz.mkdir(parents=True, exist_ok=True)
    identificador = uuid.uuid4().hex
    nombre = re.sub(r'[^\w .-]', '-', origen.name).strip(' .')[:60] or 'Documentos'
    destino = raiz / f'{nombre}-{identificador[:12]}'
    temporal = raiz / f'.importando-{identificador}'
    temporal.mkdir()
    extraidos = '_Texto_consultable'
    nombres = {a['archivo'].split('/')[0].casefold() for a in plan['archivos']}
    while extraidos.casefold() in nombres:
        extraidos += '_'
    errores, sin_texto, limitados = [], [], []
    textos_generados = 0
    try:
        for numero, entrada in enumerate(plan['archivos'], 1):
            relativa = Path(entrada['archivo'])
            fuente = origen / relativa
            # Revalida los padres: no seguir un directorio sustituido por un enlace.
            for parte in [fuente, *fuente.parents]:
                if parte == origen.parent:
                    break
                if _enlace(parte):
                    raise ValueError('La carpeta cambió durante la importación: apareció un enlace.')
            copia = temporal / relativa
            _copiar(fuente, copia)
            if copia.suffix.lower() in ('.pdf', '.txt', '.csv'):
                try:
                    texto, limitado = _extraer(copia)
                    if limitado:
                        limitados.append(entrada['archivo'])
                    if not texto.strip() and copia.suffix.lower() == '.pdf':
                        sin_texto.append(entrada['archivo'])
                    for bloque, inicio in enumerate(range(0, len(texto), 18000), 1):
                        nota = temporal / extraidos / relativa.parent / f'{relativa.name}.parte-{bloque}.md'
                        nota.parent.mkdir(parents=True, exist_ok=True)
                        nota.write_text(f'# Texto de {relativa.name}\n\nOriginal: {entrada["archivo"]}\n\n{texto[inicio:inicio + 18000]}', encoding='utf-8')
                        textos_generados += 1
                except Exception as exc:
                    errores.append({'archivo': entrada['archivo'], 'motivo': type(exc).__name__,
                                    'resumen': 'No se pudo extraer texto; se conserva el archivo original.'})
            if progreso:
                progreso(f'Copiados {numero} de {plan["total_archivos"]} archivos.')
        if destino.exists():
            raise FileExistsError('El destino ya existe; no se ha sobrescrito.')
        temporal.rename(destino)
    except BaseException:
        # Solo se elimina el staging creado por esta llamada, nunca origen ni copias previas.
        if temporal.parent.resolve() != raiz.resolve() or not temporal.name.startswith('.importando-'):
            raise RuntimeError('Ruta temporal inesperada; no se ha eliminado.')
        shutil.rmtree(temporal)
        raise
    resumen = (f'Importados {plan["total_archivos"]} archivos ({plan["bytes"] / 1024**2:.1f} MB). '
               f'{textos_generados} notas de texto creadas; {len(sin_texto)} PDF sin texto; '
               f'{len(errores)} errores de extracción; {len(plan["omitidos"])} entradas omitidas. '
               'Los originales permanecen en su carpeta. No se aplica OCR; DOCX, PPTX y hojas de cálculo se conservan como adjuntos.')
    return {**plan, 'destino': str(destino), 'textos_generados': textos_generados,
            'pdf_sin_texto': sin_texto, 'errores_extraccion': errores,
            'texto_limitado': limitados, 'resumen': resumen}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--origen', required=True)
    parser.add_argument('--boveda', required=True)
    parser.add_argument('--analizar', action='store_true')
    opciones = parser.parse_args()
    resultado = (analizar(opciones.origen, opciones.boveda) if opciones.analizar else
                 importar(opciones.origen, opciones.boveda, progreso=lambda mensaje: print(mensaje, flush=True)))
    print(json.dumps({k: resultado[k] for k in ('resumen', 'total_archivos', 'bytes', 'destino') if k in resultado}, ensure_ascii=False), flush=True)
