"""Comprueba una instalación real, sin escribir notas ni abrir interfaces de chat."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import entorno_local
from herramientas.entorno import api


def verificar():
    config = entorno_local.cargar()
    for clave in ('ollama_bin', 'opencode_bin', 'opencode_desktop_bin', 'obsidian_bin'):
        if not config.get(clave) or not Path(config[clave]).exists():
            raise RuntimeError(f'Componente ausente: {clave}')
    if not config.get('mcp_validado'):
        raise RuntimeError('La comprobación MCP no terminó correctamente.')
    respuesta = api(config, '/api/chat', {'model': config['modelo'], 'stream': False,
        'think': False, 'messages': [{'role': 'user', 'content': 'Responde solo LISTO.'}],
        'options': {'num_ctx': 2048, 'num_predict': 16, 'temperature': 0}}, timeout=180)
    contenido = respuesta.get('message', {}).get('content', '').strip()
    if not contenido:
        raise RuntimeError('El modelo no devolvió texto.')
    resultado = {'ok': True, 'modelo': config['modelo'], 'respuesta': contenido,
                 'componentes': ['ollama', 'opencode-cli', 'opencode-desktop', 'obsidian'],
                 'mcp': True, 'sistema': config['hardware']['sistema']}
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
    return resultado


if __name__ == '__main__':
    verificar()
