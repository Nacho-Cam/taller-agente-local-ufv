"""Descargas opcionales y verificadas del benchmark DSpark para Windows x64."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from herramientas.entorno import descargar, extraer

RAIZ = Path(__file__).resolve().parents[1]
DESTINO = RAIZ / '.tools/benchmark'
MODELOS = [
    ('LiquidAI/LFM3-1.7B-GGUF', 'cd0c74c575b5c416f3011b5b4c298077f26ca8c2',
     'LFM3-1.7B-Q4_K_M.gguf', '3793e1e6e2266919d6e015287221b41100175a98eddaba92e111aed3b05c93c4'),
    ('LiquidAI/LFM3-1.7B-GGUF', 'cd0c74c575b5c416f3011b5b4c298077f26ca8c2',
     'LFM3-1.7B-Q8_0.gguf', '8f6b24182258205e9e01e21f1f24a1f208c1e8115578825d202ce39976af20b6'),
    ('rasyosef/LFM3-1.7B-DSpark-GGUF', '8eb1b8ae46f7186c76cdaf861feff39ab150163d',
     'LFM3-1.7B-DSpark-Q8_0.gguf', 'ef29c215c1f4beb260206e8da18ac43797c1a45f34231ece79683ecf7865218e'),
]
BINARIO = 'llama-b12681-bin-win-vulkan-x64.zip'
SHA256 = 'c617cb1c390056af8c0614c421bfc262c00e3287a761102830a57ef1949f1b85'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--incluir-q8', action='store_true', help='Añade 1,8 GB de descarga para el target Q8.')
    args = parser.parse_args()
    archivo = DESTINO / BINARIO
    descargar('https://github.com/ggml-org/llama.cpp/releases/download/b12681/' + BINARIO,
              archivo, 'sha256', SHA256)
    binarios = DESTINO / 'llama-b12681-vulkan'
    if not (binarios / 'llama-server.exe').exists():
        extraer(archivo, binarios)
    for repo, revision, nombre, sha in MODELOS:
        if nombre == 'LFM3-1.7B-Q8_0.gguf' and not args.incluir_q8:
            continue
        descargar(f'https://huggingface.co/{repo}/resolve/{revision}/{nombre}', DESTINO / nombre, 'sha256', sha)
        (DESTINO / (nombre + '.json')).write_text(json.dumps(
            {'repo': repo, 'revision': revision, 'file': nombre, 'sha256': sha}, indent=2), encoding='utf-8')
    print('Preparado. Comprueba la GPU con llama-server --list-devices antes del benchmark.')


if __name__ == '__main__':
    main()
