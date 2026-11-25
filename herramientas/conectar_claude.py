"""Genera conexión MCP y subagente de proyecto; conserva configuraciones existentes."""
import argparse
import json
import os
import shutil
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]


def configurar(destino=RAIZ, boveda=None):
    destino = Path(destino).resolve()
    if not destino.is_dir():
        raise ValueError('El proyecto de destino debe existir.')
    boveda = Path(boveda or RAIZ / 'boveda').resolve()
    if not boveda.is_dir():
        raise ValueError('La bóveda debe existir.')
    portable = RAIZ / '.tools/uv' / ('uv.exe' if os.name == 'nt' else 'uv')
    uv = str(portable) if portable.is_file() else shutil.which('uv')
    if not uv:
        raise ValueError('Primero prepara el taller para instalar uv, o instala uv en el PATH.')
    archivo = destino / '.mcp.json'
    agente = destino / '.claude/agents/tutor-ufv.md'
    for ruta in (archivo, destino / '.claude', agente.parent, agente):
        if ruta.is_symlink():
            raise ValueError(f'No se modifica una configuración mediante enlace: {ruta}')
    config = json.loads(archivo.read_text(encoding='utf-8-sig')) if archivo.exists() else {}
    if not isinstance(config, dict):
        raise ValueError('.mcp.json debe contener un objeto JSON.')
    servidores = config.setdefault('mcpServers', {})
    if not isinstance(servidores, dict):
        raise ValueError('mcpServers debe ser un objeto JSON.')
    entrada = {'type': 'stdio', 'command': uv, 'args': ['run', '--frozen', '--directory', str(RAIZ),
        '--python', '3.11', '--extra', 'mcp', 'python', str(RAIZ / 'integraciones/servidor_mcp.py'),
        '--boveda', str(boveda)]}
    plantilla = (RAIZ / 'integraciones/claude/tutor-ufv.md').read_text(encoding='utf-8')
    if 'ufv-local' in servidores and servidores['ufv-local'] != entrada:
        raise ValueError('Ya existe otro servidor ufv-local. Revisa .mcp.json antes de sustituirlo.')
    if agente.exists() and agente.read_text(encoding='utf-8') != plantilla:
        raise ValueError('Ya existe un tutor-ufv modificado. No se ha sobrescrito.')
    servidores['ufv-local'] = entrada
    agente.parent.mkdir(parents=True, exist_ok=True)
    archivo.write_text(json.dumps(config, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    agente.write_text(plantilla, encoding='utf-8')
    return archivo, agente


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destino', type=Path, default=RAIZ, help='Proyecto que abrirás con Claude Code.')
    parser.add_argument('--boveda', type=Path, help='Por defecto, la bóveda de este taller.')
    args = parser.parse_args()
    try:
        for ruta in configurar(args.destino, args.boveda):
            print(ruta)
        print('Abre Claude Code en ese proyecto. Comprueba /mcp y /agents.')
    except (OSError, ValueError, TypeError) as error:
        parser.exit(1, f'No se ha podido configurar: {error}\n')
