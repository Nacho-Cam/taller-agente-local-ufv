"""Instalación por usuario, actualización conservadora y accesos del sistema."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile

CARPETA = 'taller-agente-local-ufv'
MARCADOR = '.ufv-paquete.json'
PRESERVADOS = {'boveda', '.local', '.tools', '.venv', 'opencode.json', '.git'}


def ruta_predeterminada(sistema=None, entorno=None, home=None):
    sistema = sistema or platform.system()
    ambiente = os.environ if entorno is None else entorno
    casa = Path.home() if home is None else Path(home)
    if sistema == 'Windows':
        return Path(ambiente.get('LOCALAPPDATA', casa / 'AppData/Local')) / 'Programs/TallerUFV'
    if sistema == 'Darwin':
        return casa / 'Library/Application Support/TallerUFV'
    return Path(ambiente.get('XDG_DATA_HOME') or casa / '.local/share') / 'taller-ufv'


def _hash(archivo):
    calculo = hashlib.sha256()
    with Path(archivo).open('rb') as entrada:
        for bloque in iter(lambda: entrada.read(1024 * 1024), b''):
            calculo.update(bloque)
    return calculo.hexdigest()


def _segura(raiz, relativa):
    """Rechaza también enlaces/junctions en cualquier padre existente."""
    partes = PurePosixPath(relativa).parts
    if (not partes or '\\' in relativa or ':' in relativa or relativa.startswith('/')
            or any(p in ('', '.', '..') or p.endswith((' ', '.')) for p in relativa.split('/'))):
        raise ValueError('El paquete contiene una ruta no permitida.')
    ruta = raiz
    for parte in partes:
        ruta = ruta / parte
        if ruta.is_symlink() or (ruta.exists() and getattr(ruta.lstat(), 'st_file_attributes', 0) & 0x400):
            raise ValueError('No se admiten enlaces ni junctions en la instalación.')
    if raiz.resolve() not in ruta.resolve().parents:
        raise ValueError('Ruta fuera de la instalación.')
    return ruta


def instalacion_valida(proyecto, sha256=None):
    """Comprueba los archivos gestionados para poder abrir sin descargar nada."""
    proyecto = Path(proyecto)
    try:
        meta = json.loads((proyecto / MARCADOR).read_text(encoding='utf-8'))
        if sha256 and meta.get('sha256') != sha256:
            return False
        if not (proyecto / 'preparar.ps1').is_file() or not (proyecto / 'iniciar.sh').is_file():
            return False
        archivos = meta.get('archivos')
        if archivos is None:  # Marcadores de versiones antiguas.
            return True
        return bool(archivos) and all(_hash(_segura(proyecto, n)) == sha for n, sha in archivos.items())
    except (OSError, ValueError, TypeError, AttributeError):
        return False


def actualizar_paquete(archivo, destino, sha256, version):
    """Actualiza código con rollback; conserva íntegros notas, modelos y ajustes.

    Un archivo de código editado localmente bloquea la actualización antes de
    tocar nada. Los archivos ajenos al manifiesto no se eliminan ni reemplazan.
    """
    archivo, destino = Path(archivo), Path(destino).absolute()
    if _hash(archivo) != sha256:
        raise ValueError('El ZIP no coincide con el SHA256 de esta versión.')
    destino.mkdir(parents=True, exist_ok=True)
    proyecto = _segura(destino, CARPETA)
    meta_anterior = None
    if proyecto.exists():
        try:
            meta_anterior = json.loads((proyecto / MARCADOR).read_text(encoding='utf-8'))
        except (OSError, ValueError) as error:
            raise ValueError('La carpeta contiene una instalación sin manifiesto. Elige otra carpeta para conservarla.') from error
        if meta_anterior.get('sha256') == sha256 and instalacion_valida(proyecto, sha256):
            return proyecto
        if not isinstance(meta_anterior.get('archivos'), dict):
            raise ValueError('Esta instalación antigua no permite actualizar código con seguridad. Conserva su carpeta y elige otra.')
        for nombre, esperado in meta_anterior['archivos'].items():
            actual = _segura(proyecto, nombre)
            if not actual.is_file() or _hash(actual) != esperado:
                raise ValueError(f'Hay código modificado o ausente: {nombre}. Conserva los cambios antes de actualizar.')
    with tempfile.TemporaryDirectory(prefix='.ufv-actualizar-', dir=destino) as temporal:
        temporal = Path(temporal)
        extraido = temporal / 'nuevo'
        extraido.mkdir()
        nombres = set()
        with zipfile.ZipFile(archivo) as paquete:
            for entrada in paquete.infolist():
                nombre = entrada.filename
                if not nombre.startswith(CARPETA + '/'):
                    raise ValueError('El ZIP contiene una ruta fuera de la carpeta del taller.')
                relativa = nombre[len(CARPETA) + 1:].rstrip('/')
                if not relativa:
                    continue
                ruta = _segura(extraido, relativa)
                if relativa == MARCADOR or stat.S_ISLNK(entrada.external_attr >> 16):
                    raise ValueError('El paquete contiene enlaces o metadatos no permitidos.')
                clave = relativa.casefold()
                if clave in nombres:
                    raise ValueError('El paquete contiene rutas duplicadas.')
                nombres.add(clave)
                if entrada.is_dir():
                    ruta.mkdir(parents=True, exist_ok=True)
                else:
                    ruta.parent.mkdir(parents=True, exist_ok=True)
                    with paquete.open(entrada) as origen, ruta.open('wb') as salida:
                        shutil.copyfileobj(origen, salida)
                    if entrada.external_attr >> 16 & 0o111:
                        ruta.chmod(ruta.stat().st_mode | 0o111)
        if not (extraido / 'preparar.ps1').is_file() or not (extraido / 'iniciar.sh').is_file():
            raise ValueError('El ZIP no contiene los lanzadores del taller.')
        archivos = {p.relative_to(extraido).as_posix(): _hash(p) for p in extraido.rglob('*')
                    if p.is_file() and p.relative_to(extraido).parts[0] not in PRESERVADOS}
        manifiesto = {'version': version, 'sha256': sha256, 'archivos': archivos}
        (extraido / MARCADOR).write_text(json.dumps(manifiesto, ensure_ascii=False, indent=2), encoding='utf-8')
        if meta_anterior is None:
            if proyecto.exists():
                raise ValueError('La carpeta de destino apareció durante la instalación; inténtalo de nuevo.')
            extraido.replace(proyecto)
            return proyecto
        anteriores = set(meta_anterior['archivos'])
        for nombre in archivos:
            actual = _segura(proyecto, nombre)
            if nombre not in anteriores and actual.exists():
                raise ValueError(f'El nuevo paquete coincide con un archivo personal: {nombre}.')
        # Preparar todas las copias antes de cambiar código, luego revertir ante errores.
        respaldo = temporal / 'respaldo'
        respaldo.mkdir()
        cambios = sorted(anteriores | set(archivos)) + [MARCADOR]
        existentes = set()
        for nombre in cambios:
            actual = _segura(proyecto, nombre)
            if actual.exists():
                copia = _segura(respaldo, nombre)
                copia.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(actual, copia)
                existentes.add(nombre)
        tocados = []
        try:
            for nombre in cambios:
                actual, nuevo = _segura(proyecto, nombre), _segura(extraido, nombre)
                tocados.append(nombre)
                if nuevo.is_file():
                    actual.parent.mkdir(parents=True, exist_ok=True)
                    nuevo.replace(actual)
                elif actual.exists():
                    actual.unlink()
        except BaseException:
            for nombre in reversed(tocados):
                actual = _segura(proyecto, nombre)
                if nombre in existentes:
                    shutil.copy2(_segura(respaldo, nombre), actual)
                elif actual.exists():
                    actual.unlink()
            raise
    return proyecto


def comando_arranque(proyecto, accion='iniciar', componentes=None):
    proyecto = Path(proyecto).resolve()
    if accion not in {'iniciar', 'preparar', 'notas', 'doctor', 'equipo', 'terminal'}:
        raise ValueError('Acción de arranque no permitida.')
    if platform.system() == 'Windows':
        comando = ['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
                   str(proyecto / 'preparar.ps1'), '-Accion', accion]
        if componentes is not None:
            comando += ['-Componentes', str(Path(componentes).resolve())]
        return comando
    comando = ['/bin/sh', str(proyecto / 'iniciar.sh'), accion]
    if componentes is not None:
        comando += ['--componentes', str(Path(componentes).resolve())]
    return comando


def _copiar_binario(ejecutable, destino):
    """Nombres por contenido permiten actualizar incluso con el EXE abierto."""
    destino.mkdir(parents=True, exist_ok=True)
    copia = destino / ('Taller-UFV-' + _hash(ejecutable)[:12] + Path(ejecutable).suffix)
    if not copia.exists():
        shutil.copy2(ejecutable, copia)
        copia.chmod(copia.stat().st_mode | stat.S_IXUSR)
    return copia


def _desktop_quote(texto):
    return '"' + str(texto).replace('\\', '\\\\').replace('"', '\\"').replace('`', '\\`').replace('$', '\\$').replace('%', '%%') + '"'


def crear_accesos(destino, ejecutable, sistema=None):
    """Conserva el instalador y registra una aplicación por usuario, sin sudo."""
    sistema = sistema or platform.system()
    destino, ejecutable = Path(destino).resolve(), Path(ejecutable).resolve()
    destino.mkdir(parents=True, exist_ok=True)
    if ejecutable.suffix == '.py':
        comando = [sys.executable, str(ejecutable)]
    else:
        comando = [str(_copiar_binario(ejecutable, destino / 'lanzador'))]
    comando += ['--abrir', '--destino', str(destino)]
    if sistema == 'Windows':
        enlace = Path(os.environ.get('APPDATA', Path.home() / 'AppData/Roaming')) / 'Microsoft/Windows/Start Menu/Programs/Taller UFV.lnk'
        enlace.parent.mkdir(parents=True, exist_ok=True)
        ambiente = dict(os.environ, UFV_LANZADOR=comando[0], UFV_ENLACE=str(enlace),
                        UFV_ARGUMENTOS=subprocess.list2cmdline(comando[1:]), UFV_DIRECTORIO=str(destino))
        subprocess.run(['powershell.exe', '-NoProfile', '-Command',
                        '$taskShell=New-Object -ComObject WScript.Shell; '
                        '$taskLink=$taskShell.CreateShortcut($env:UFV_ENLACE); '
                        '$taskLink.TargetPath=$env:UFV_LANZADOR; $taskLink.Arguments=$env:UFV_ARGUMENTOS; '
                        '$taskLink.WorkingDirectory=$env:UFV_DIRECTORIO; '
                        '$taskLink.Description="Tu agente local de la universidad"; $taskLink.Save()'],
                       env=ambiente, check=True, timeout=20,
                       creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0) if os.name == 'nt' else 0)
        return enlace
    if sistema == 'Darwin':
        app = Path.home() / 'Applications/Taller UFV.app'
        macos = app / 'Contents/MacOS'
        macos.mkdir(parents=True, exist_ok=True)
        # Un bundle de PyInstaller necesita sus Resources/Frameworks junto al ejecutable.
        paquete = next((p for p in ejecutable.parents if p.suffix == '.app'), None)
        if paquete and ejecutable.suffix != '.py':
            estable = destino / 'lanzador' / ('app-' + _hash(ejecutable)[:12] + '.app')
            if not estable.exists():
                shutil.copytree(paquete, estable, symlinks=True)
            comando[0] = str(estable / ejecutable.relative_to(paquete))
        lanzador = macos / 'TallerUFV'
        lanzador.write_text('#!/bin/sh\nexec ' + shlex.join(comando) + '\n', encoding='utf-8')
        lanzador.chmod(0o755)
        (app / 'Contents/Info.plist').write_text('''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict><key>CFBundleName</key><string>Taller UFV</string>
<key>CFBundleIdentifier</key><string>es.ufv.taller-local</string>
<key>CFBundleExecutable</key><string>TallerUFV</string>
<key>CFBundlePackageType</key><string>APPL</string></dict></plist>''', encoding='utf-8')
        return app
    aplicaciones = Path(os.environ.get('XDG_DATA_HOME') or Path.home() / '.local/share') / 'applications'
    aplicaciones.mkdir(parents=True, exist_ok=True)
    acceso = aplicaciones / 'taller-ufv.desktop'
    acceso.write_text('[Desktop Entry]\nType=Application\nName=Taller UFV\n'
                      'Comment=Tu agente local de la universidad\nTerminal=false\nCategories=Education;\n'
                      'Exec=' + ' '.join(_desktop_quote(p) for p in comando) + '\n', encoding='utf-8')
    acceso.chmod(0o755)
    return acceso
