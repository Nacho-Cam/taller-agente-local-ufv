"""Prueba el lanzador POSIX real sin descargar Python, modelos ni aplicaciones."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


@unittest.skipIf(os.name == 'nt', 'El lanzador POSIX se ejecuta en runners macOS y Linux.')
class ArranquePOSIX(unittest.TestCase):
    def test_abre_desde_otra_carpeta_y_conserva_argumentos_con_espacios(self):
        origen = Path(__file__).resolve().parents[1] / 'iniciar.sh'
        with tempfile.TemporaryDirectory() as temporal:
            raiz = Path(temporal) / 'Mi universidad con espacios'
            uv = raiz / '.tools/uv/uv'
            uv.parent.mkdir(parents=True)
            shutil.copyfile(origen, raiz / 'iniciar.sh')
            uv.write_text('#!/bin/sh\nprintf "%s\\n" "$PWD" "$@" > "$UFV_TEST_CAPTURE"\n', encoding='utf-8')
            uv.chmod(0o755)
            captura = Path(temporal) / 'argumentos.txt'
            for entrada, esperados in [
                ([], ['iniciar']),
                (['preparar', '--ui', 'no', '--componentes', 'seleccion con espacios.json'],
                 ['preparar', '--ui', 'no', '--componentes', 'seleccion con espacios.json']),
            ]:
                with self.subTest(argumentos=entrada):
                    subprocess.run(['sh', str(raiz / 'iniciar.sh'), *entrada], cwd=temporal,
                                   env=dict(os.environ, UFV_TEST_CAPTURE=str(captura)),
                                   check=True, timeout=10, capture_output=True)
                    lineas = captura.read_text(encoding='utf-8').splitlines()
                    self.assertEqual(Path(lineas[0]).resolve(), raiz.resolve())
                    self.assertEqual(lineas[1:], ['run', '--python', '3.11', '--extra', 'mcp',
                                                 'herramientas/entorno.py', *esperados])


if __name__ == '__main__':
    unittest.main()
