"""Elección persistente e instalación opcional de OpenCode Desktop 2."""
import json
import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote

RAIZ = Path(__file__).resolve().parents[1]
PREFERENCIAS = RAIZ / '.local/interfaz.json'
VERSION = '2.4.1'
HASHES = {
    'opencode-desktop-win-x64.exe': 'e144d723c07ee3d724b4c0bbab0297adc9d9554ec9c4574e33fc9df1b2318a35',
    'opencode-desktop-win-arm64.exe': 'f140240840f3f6c5a517cf3dfee7ff36fed82122f47104d882fe02bb6ec78e0e',
    'opencode-desktop-mac-arm64.app.tar.gz': '2514513623292058fcd75513abae997a8ac59dd288a441e4be5fd0f8c5c9a51c',
    'opencode-desktop-mac-x64.app.tar.gz': 'e3f1dd72cf31a919f09bc6cf8591a3bed3481d1581faff57099dc634c54e8bdc',
    'opencode-desktop-linux-arm64.AppImage': '55f1d2de1415c913ad82c46c269ae57f22462ce341928e00bfbc2b2540887fc9',
    'opencode-desktop-linux-x86_64.AppImage': '0b68c8f5a6d1ad992815c026bb90a56e43d9e3db37c7fba5ea3f6094080b9a33',
}


def elegir(opcion='auto'):
    """En modo no interactivo se conserva el recorrido ligero salvo elección explícita."""
    if opcion == 'auto' and PREFERENCIAS.exists():
        datos = json.loads(PREFERENCIAS.read_text(encoding='utf-8'))
        if not isinstance(datos, dict) or type(datos.get('escritorio')) is not bool:
            raise ValueError('Preferencia de interfaz no válida; usa --ui si o --ui no.')
        return datos['escritorio']
    if opcion in ('auto', 'elegir'):
        if sys.stdin.isatty():
            print('\nInterfaz del tutor:\n  1. Instalar y usar OpenCode Desktop (ventana gráfica).\n  2. Solo terminal (sin instalar la aplicación de escritorio).', flush=True)
            while True:
                try:
                    respuesta = input('Elige 1 o 2 [2]: ').strip()
                except EOFError:
                    respuesta = ''
                if respuesta in ('', '1', '2'):
                    opcion = 'si' if respuesta == '1' else 'no'
                    break
                print('Escribe 1 o 2.')
        else:
            print('Sin selección interactiva: se usará solo terminal. Para instalar la app, usa --ui si.', flush=True)
            return False  # No convierte un arranque automatizado en una elección permanente.
    escritorio = opcion == 'si'
    PREFERENCIAS.parent.mkdir(parents=True, exist_ok=True)
    PREFERENCIAS.write_text(json.dumps({'escritorio': escritorio}, indent=2), encoding='utf-8')
    return escritorio


def instalado(sistema):
    destino = RAIZ / '.tools/opencode-desktop' / VERSION
    if sistema == 'Windows':
        local = Path(os.environ['LOCALAPPDATA'])
        candidatos = [local / 'Programs/ai.opencode.desktop/OpenCode.exe', destino / 'OpenCode.exe']
    elif sistema == 'Darwin':
        candidatos = list(destino.glob('*.app'))
    else:
        candidatos = [destino / 'squashfs-root/AppRun']
    return next((str(p) for p in candidatos if p.exists()), None)


def instalar(hardware):
    from herramientas.entorno import descargar, extraer
    sistema = hardware['sistema']
    existente = instalado(sistema)
    if existente:
        print('OpenCode Desktop ya disponible; se reutiliza.', flush=True)
        return existente
    arm = hardware['arquitectura'] in ('arm64', 'aarch64')
    nombres = {
        'Windows': f'opencode-desktop-win-{"arm64" if arm else "x64"}.exe',
        'Darwin': f'opencode-desktop-mac-{"arm64" if arm else "x64"}.app.tar.gz',
        'Linux': f'opencode-desktop-linux-{"arm64" if arm else "x86_64"}.AppImage',
    }
    if sistema not in nombres:
        raise ValueError('Sistema no compatible con OpenCode Desktop.')
    nombre = nombres[sistema]
    archivo = RAIZ / '.tools/descargas' / nombre
    descargar(f'https://github.com/anomalyco/opencode/releases/download/v{VERSION}/{nombre}', archivo, 'sha256', HASHES[nombre])
    destino = RAIZ / '.tools/opencode-desktop' / VERSION
    if sistema == 'Windows':
        subprocess.run([str(archivo), '/S', '/currentuser'], check=True, timeout=300,
                       creationflags=subprocess.CREATE_NO_WINDOW)
    elif sistema == 'Darwin':
        extraer(archivo, destino)
    else:
        destino.mkdir(parents=True, exist_ok=True)
        archivo.chmod(archivo.stat().st_mode | 0o111)
        subprocess.run([str(archivo), '--appimage-extract'], cwd=destino, check=True,
                       stdout=subprocess.DEVNULL, timeout=180)
    binario = instalado(sistema)
    if not binario:
        raise RuntimeError('No se encontró OpenCode Desktop tras instalarlo. Puedes continuar con --ui no.')
    return binario


def abrir(binario, sistema, espacio):
    # Enlace soportado por Desktop 2: abre el proyecto con su configuración local.
    uri = 'opencode://open-project?directory=' + quote(str(Path(espacio).resolve()), safe='')
    comando = ['open', '-a', binario, uri] if sistema == 'Darwin' else [binario, uri]
    opciones = {'creationflags': subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP} if sistema == 'Windows' else {'start_new_session': True}
    subprocess.Popen(comando, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **opciones)
