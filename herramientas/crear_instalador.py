"""Construye un instalador gráfico nativo con el hash del ZIP canónico."""
import hashlib
import json
import subprocess
import sys
import platform
import tarfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
VERSION = '0.8.1'


if __name__ == '__main__':
    archivo = RAIZ / 'dist/taller-agente-local-ufv.zip'
    recurso = RAIZ / '.local/instalador-build.json'
    recurso.parent.mkdir(exist_ok=True)
    recurso.write_text(json.dumps({'version': VERSION,
        'url': f'https://github.com/Nacho-Cam/taller-agente-local-ufv/releases/download/v{VERSION}/{archivo.name}',
        'sha256': hashlib.sha256(archivo.read_bytes()).hexdigest()}, indent=2), encoding='utf-8')
    sistema = platform.system()
    argumentos = [sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--onefile', '--windowed',
        '--name', 'Instalar-Taller-UFV', '--distpath', str(RAIZ / 'dist'),
        '--workpath', str(RAIZ / '.local/pyinstaller'), '--specpath', str(RAIZ / '.local'),
        '--paths', str(RAIZ / 'herramientas'), '--add-data', str(recurso) + (';.' if sistema == 'Windows' else ':.'),
        str(RAIZ / 'herramientas/instalador_ui.py')]
    if sistema == 'Darwin':
        argumentos[argumentos.index('--onefile')] = '--onedir'
        argumentos.extend(['--osx-bundle-identifier', 'es.ufv.taller.agente'])
    subprocess.run(argumentos, check=True)
    arch = platform.machine().lower()
    if sistema == 'Darwin':
        app = RAIZ / 'dist/Instalar-Taller-UFV.app'
        salida = RAIZ / f'dist/Instalar-Taller-UFV-macOS-{arch}.zip'
        # ditto conserva permisos, symlinks y estructura de un bundle macOS.
        subprocess.run(['ditto', '-c', '-k', '--sequesterRsrc', '--keepParent', str(app), str(salida)], check=True)
    elif sistema == 'Linux':
        with tarfile.open(RAIZ / f'dist/Instalar-Taller-UFV-Linux-{arch}.tar.gz', 'w:gz') as paquete:
            paquete.add(RAIZ / 'dist/Instalar-Taller-UFV', arcname='Instalar-Taller-UFV')
