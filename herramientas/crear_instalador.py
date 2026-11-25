"""Construye el EXE Windows fijando el hash del ZIP que se publicará en GitHub."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
VERSION = '0.5.0'


if __name__ == '__main__':
    archivo = RAIZ / 'dist/taller-agente-local-ufv.zip'
    recurso = RAIZ / '.local/instalador-build.json'
    recurso.parent.mkdir(exist_ok=True)
    recurso.write_text(json.dumps({'version': VERSION,
        'url': f'https://github.com/Nacho-Cam/taller-agente-local-ufv/releases/download/v{VERSION}/{archivo.name}',
        'sha256': hashlib.sha256(archivo.read_bytes()).hexdigest()}, indent=2), encoding='utf-8')
    subprocess.run([sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--onefile', '--console',
        '--name', 'Instalar-Taller-UFV', '--distpath', str(RAIZ / 'dist'),
        '--workpath', str(RAIZ / '.local/pyinstaller'), '--specpath', str(RAIZ / '.local'),
        '--add-data', str(recurso) + ';.', str(RAIZ / 'herramientas/instalador_windows.py')], check=True)
