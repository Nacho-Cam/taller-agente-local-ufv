"""Arranque Windows empaquetable como EXE. Descarga una versión fijada y verificada."""
import argparse
import hashlib
import json
import os
import shutil
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
from urllib.request import urlopen
import zipfile

CARPETA = 'taller-agente-local-ufv'


def crear_acceso(destino, version):
    if not getattr(sys, 'frozen', False):
        return
    destino = Path(destino).resolve()
    lanzador = destino / 'Abrir-Taller-UFV.exe'
    if Path(sys.executable).resolve() != lanzador:
        shutil.copy2(sys.executable, lanzador)
    enlace = Path(os.environ['APPDATA']) / f'Microsoft/Windows/Start Menu/Programs/Taller UFV {version}.lnk'
    ambiente = dict(os.environ, UFV_LANZADOR=str(lanzador), UFV_ENLACE=str(enlace),
                    UFV_ARGUMENTOS=subprocess.list2cmdline(['--destino', str(destino)]))
    subprocess.run(['powershell.exe', '-NoProfile', '-Command',
        '$taskShell=New-Object -ComObject WScript.Shell; '
        '$taskLink=$taskShell.CreateShortcut($env:UFV_ENLACE); '
        '$taskLink.TargetPath=$env:UFV_LANZADOR; $taskLink.Arguments=$env:UFV_ARGUMENTOS; '
        '$taskLink.Description="Iniciar el modelo, las notas y el tutor local UFV"; $taskLink.Save()'],
        env=ambiente, check=True, timeout=20, creationflags=subprocess.CREATE_NO_WINDOW)
    print(f'Acceso disponible en Inicio: Taller UFV {version}.', flush=True)


def extraer_paquete(archivo, destino, esperado):
    destino = Path(destino).resolve()
    if hashlib.sha256(Path(archivo).read_bytes()).hexdigest() != esperado:
        raise ValueError('El ZIP no coincide con el SHA256 de esta versión.')
    proyecto = destino / CARPETA
    marcador = proyecto / '.ufv-paquete.json'
    if proyecto.exists():
        if marcador.is_file() and json.loads(marcador.read_text())['sha256'] == esperado:
            return proyecto
        raise ValueError('La carpeta de destino ya contiene otro taller. Elige otra carpeta con --destino.')
    with zipfile.ZipFile(archivo) as z:
        for entrada in z.infolist():
            ruta = (destino / entrada.filename).resolve()
            if proyecto not in ruta.parents and ruta != proyecto:
                raise ValueError('El ZIP contiene una ruta fuera de la carpeta del taller.')
            if stat.S_ISLNK(entrada.external_attr >> 16):
                raise ValueError('No se admiten enlaces en el paquete.')
        if CARPETA + '/preparar.ps1' not in z.namelist():
            raise ValueError('El ZIP no contiene el instalador del taller.')
        destino.mkdir(parents=True, exist_ok=True)
        z.extractall(destino)
    marcador.write_text(json.dumps({'sha256': esperado}), encoding='utf-8')
    return proyecto


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destino', type=Path)
    parser.add_argument('--accion', choices=['iniciar', 'preparar', 'notas', 'doctor'], default='iniciar')
    parser.add_argument('--ui', choices=['auto', 'si', 'no', 'elegir'], default='auto', help='Instalar/usar Desktop o solo terminal; auto recuerda la elección.')
    args = parser.parse_args()
    recurso = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent)) / 'instalador-build.json'
    meta = json.loads(recurso.read_text(encoding='utf-8'))
    destino = args.destino or Path(os.environ['LOCALAPPDATA']) / 'Programs/TallerUFV' / meta['version']
    print(f'Taller UFV {meta["version"]}\nInstalación: {destino}\n', flush=True)
    try:
        proyecto = destino / CARPETA
        marcador = proyecto / '.ufv-paquete.json'
        if marcador.is_file() and json.loads(marcador.read_text())['sha256'] == meta['sha256'] and (proyecto / 'preparar.ps1').is_file():
            print('Se reutiliza el taller instalado; no hace falta descargar el ZIP.', flush=True)
        else:
            with tempfile.TemporaryDirectory(prefix='ufv-descarga-') as temporal:
                archivo = Path(temporal) / 'taller.zip'
                print('Descargando el material oficial del repositorio...', flush=True)
                with urlopen(meta['url'], timeout=60) as respuesta, archivo.open('wb') as salida:
                    while bloque := respuesta.read(1024 * 1024):
                        salida.write(bloque)
                proyecto = extraer_paquete(archivo, destino, meta['sha256'])
        print('Paquete verificado. Preparando el entorno; la primera vez puede tardar varios minutos.', flush=True)
        if sys.platform == 'win32' and getattr(sys, 'frozen', False):
            import ctypes
            # No propagar a Python/Ollama las DLL temporales del propio EXE.
            ctypes.windll.kernel32.SetDllDirectoryW(None)
        resultado = subprocess.call(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass',
            '-File', str(proyecto / 'preparar.ps1'), '-Accion', args.accion, '-UI', args.ui], cwd=proyecto,
            env=dict(os.environ, _PYI_RESET_ENVIRONMENT='1'))
        if resultado:
            raise RuntimeError(f'La preparación devolvió el código {resultado}. Revisa el mensaje anterior.')
        crear_acceso(destino, meta['version'])
        print(f'Listo. El taller queda en:\n{proyecto}', flush=True)
        return 0
    except (OSError, ValueError, RuntimeError, zipfile.BadZipFile) as error:
        print(f'No se completó la instalación: {error}', file=sys.stderr, flush=True)
        return 1
    finally:
        if len(sys.argv) == 1 and sys.stdin.isatty():
            input('\nPulsa Enter para cerrar esta ventana...')


if __name__ == '__main__':
    sys.exit(main())
