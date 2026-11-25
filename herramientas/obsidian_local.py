"""Instala Obsidian para el usuario y abre la bóveda sin alterar otras bóvedas."""
import json
import os
import plistlib
import shutil
import subprocess
import hashlib
import tempfile
import time
from pathlib import Path
from urllib.parse import quote

RAIZ = Path(__file__).resolve().parents[1]
VERSION = '1.15.1'
HASHES = {
    'Obsidian-1.15.1.exe': '218c7d30acc065355ce94719dd996d5e2a2347cde3811ea5dc29380583f02b58',
    'Obsidian-1.15.1.dmg': 'e05c7e3e2262b14c965bb246dcb74a30fc9098bd669e42957c4d9f788d04fdf4',
    'obsidian-1.15.1.tar.gz': '09074f0635ecf366307d808d0fec06c01a87a0bcc66da6d34126ceece0eb8519',
    'obsidian-1.15.1-arm64.tar.gz': 'acc219e57e2630c4936e7655126572b62167ea02c2e66f8c25c948ad072b4e70',
}


def instalado(sistema):
    if sistema == 'Windows':
        local = Path(os.environ.get('LOCALAPPDATA', str(Path.home() / 'AppData/Local')))
        candidatos = [local / 'Programs/Obsidian/Obsidian.exe', local / 'Obsidian/Obsidian.exe',
                      Path(os.environ.get('ProgramFiles', 'C:/Program Files')) / 'Obsidian/Obsidian.exe']
    elif sistema == 'Darwin':
        candidatos = [Path.home() / 'Applications/Obsidian.app', Path('/Applications/Obsidian.app')]
    else:
        candidatos = [Path(p) for p in [shutil.which('obsidian')] if p]
        candidatos += list((RAIZ / '.tools/obsidian' / VERSION).rglob('obsidian'))
    return next((str(p) for p in candidatos if p.exists() and (sistema == 'Darwin' or p.is_file())), None)


def instalar(hardware):
    from herramientas.entorno import descargar, extraer
    sistema = hardware['sistema']
    existente = instalado(sistema)
    if existente:
        print('Obsidian ya instalado; se reutiliza.', flush=True)
        return existente
    arm = hardware['arquitectura'] in ('arm64', 'aarch64')
    nombre = {'Windows': f'Obsidian-{VERSION}.exe', 'Darwin': f'Obsidian-{VERSION}.dmg',
              'Linux': f'obsidian-{VERSION}{"-arm64" if arm else ""}.tar.gz'}.get(sistema)
    if nombre is None:
        raise RuntimeError('Sistema no compatible con Obsidian automático.')
    archivo = RAIZ / '.tools/descargas' / nombre
    descargar(f'https://github.com/obsidianmd/obsidian-releases/releases/download/v{VERSION}/{nombre}',
              archivo, 'sha256', HASHES[nombre])
    if sistema == 'Windows':
        subprocess.run([str(archivo), '/S', '/currentuser'], check=True, timeout=240,
                       creationflags=subprocess.CREATE_NO_WINDOW)
    elif sistema == 'Darwin':
        salida = subprocess.check_output(['hdiutil', 'attach', '-nobrowse', '-readonly', '-plist', str(archivo)], timeout=90)
        montaje = next(e['mount-point'] for e in plistlib.loads(salida)['system-entities'] if 'mount-point' in e)
        try:
            destino = Path.home() / 'Applications/Obsidian.app'
            destino.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(Path(montaje) / 'Obsidian.app', destino, symlinks=True)
        finally:
            subprocess.run(['hdiutil', 'detach', montaje], check=True, timeout=30)
    else:
        destino = RAIZ / '.tools/obsidian' / VERSION
        extraer(archivo, destino)
        for ejecutable in destino.rglob('obsidian'):
            if ejecutable.is_file():
                ejecutable.chmod(ejecutable.stat().st_mode | 0o111)
    binario = instalado(sistema)
    if not binario:
        raise RuntimeError('No se encontró Obsidian después de instalarlo.')
    return binario


def registro(sistema):
    if sistema == 'Windows':
        return Path(os.environ.get('APPDATA', str(Path.home() / 'AppData/Roaming'))) / 'obsidian/obsidian.json'
    if sistema == 'Darwin':
        return Path.home() / 'Library/Application Support/obsidian/obsidian.json'
    return Path(os.environ.get('XDG_CONFIG_HOME', str(Path.home() / '.config'))) / 'obsidian/obsidian.json'


def boveda_conocida(sistema, boveda):
    try:
        datos = json.loads(registro(sistema).read_text(encoding='utf-8-sig'))
        if not isinstance(datos, dict) or not isinstance(datos.get('vaults', {}), dict):
            return False
        return any(Path(v['path']).resolve() == Path(boveda).resolve() for v in datos.get('vaults', {}).values())
    except (OSError, ValueError, KeyError, TypeError):
        return False


def cerrar_para_registrar(sistema, binario):
    """Cierre normal para que Obsidian guarde su estado antes de modificar su registro."""
    import psutil
    usuario = psutil.Process().username()
    procesos = []
    for proceso in psutil.process_iter(['exe', 'username']):
        try:
            exe = Path(proceso.info['exe'] or '').resolve()
            coincide = exe == Path(binario).resolve() if sistema != 'Darwin' else Path(binario).resolve() in exe.parents
            if coincide and proceso.info['username'] == usuario:
                procesos.append(proceso)
        except (OSError, psutil.Error):
            continue
    if not procesos:
        return
    print('Obsidian se reiniciará para añadir la bóveda del taller; se conservarán las otras bóvedas.', flush=True)
    if sistema == 'Windows':
        import ctypes
        from ctypes import wintypes
        usuario32 = ctypes.windll.user32
        usuario32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
        usuario32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
        pids = {p.pid for p in procesos}
        tipo = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        def cerrar(ventana, _):
            pid = wintypes.DWORD()
            usuario32.GetWindowThreadProcessId(ventana, ctypes.byref(pid))
            if pid.value in pids:
                usuario32.PostMessageW(ventana, 0x0010, 0, 0)  # WM_CLOSE, sin terminar a la fuerza.
            return True
        usuario32.EnumWindows(tipo(cerrar), 0)
    elif sistema == 'Darwin':
        subprocess.run(['osascript', '-e', 'tell application "Obsidian" to quit'], check=True, timeout=15)
    else:
        for proceso in procesos:
            proceso.terminate()
    _, pendientes = psutil.wait_procs(procesos, timeout=10)
    if pendientes:
        raise RuntimeError('Obsidian no ha terminado su cierre normal. Ciérralo y repite; no se ha modificado su registro.')


def registrar_boveda(sistema, binario, boveda):
    boveda = Path(boveda).resolve()
    if boveda_conocida(sistema, boveda):
        return
    cerrar_para_registrar(sistema, binario)
    archivo = registro(sistema)
    if archivo.is_symlink():
        raise ValueError('El registro de Obsidian es un enlace; no se modifica automáticamente.')
    anterior = archivo.read_bytes() if archivo.exists() else None
    datos = json.loads(anterior.decode('utf-8-sig')) if anterior else {}
    if not isinstance(datos, dict) or not isinstance(datos.get('vaults', {}), dict):
        raise ValueError('Formato de registro Obsidian desconocido; no se ha modificado.')
    vaults = datos.setdefault('vaults', {})
    clave = hashlib.sha256(str(boveda).encode('utf-8')).hexdigest()[:16]
    if clave in vaults and Path(vaults[clave]['path']).resolve() != boveda:
        raise ValueError('Colisión de identificador de bóveda; no se ha modificado el registro.')
    vaults[clave] = {'path': str(boveda), 'ts': int(time.time() * 1000), 'open': True}
    archivo.parent.mkdir(parents=True, exist_ok=True)
    copia = archivo.with_name('obsidian.json.ufv-backup')
    if anterior is not None and not copia.exists():
        with copia.open('xb') as salida:
            salida.write(anterior)
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=archivo.parent, prefix='.ufv-', suffix='.tmp', delete=False) as salida:
        json.dump(datos, salida, ensure_ascii=False)
        temporal = Path(salida.name)
    temporal.replace(archivo)


def lanzar(binario, sistema, uri):
    if sistema == 'Windows':
        os.startfile(uri)
    else:
        comando = ['open', '-a', binario, uri] if sistema == 'Darwin' else [binario, uri]
        subprocess.Popen(comando, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def abrir(binario, sistema, boveda=None):
    boveda = Path(boveda or RAIZ / 'boveda').resolve()
    if not boveda.is_dir():
        raise ValueError('No existe la bóveda del taller.')
    registrar_boveda(sistema, binario, boveda)
    uri = 'obsidian://open?path=' + quote(str(boveda / 'Inicio.md'), safe='')
    lanzar(binario, sistema, uri)
    return True
