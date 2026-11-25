"""Genera un ZIP reproducible en contenido, sin notas personales ni cachés."""
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

RAIZ = Path(__file__).resolve().parents[1]
DESTINO = RAIZ / "dist" / "taller-agente-local-ufv.zip"
CARPETAS = ("solucion", "plantilla", "docs", "tests", "herramientas", "boveda/apuntes")


def empaquetar():
    nombres = ("README.md", ".gitignore", ".gitattributes", "nucleo.py", "entorno_local.py", "pyproject.toml", "uv.lock",
               "preparar.ps1", "iniciar.cmd", "iniciar.sh", "boveda/Inicio.md", "boveda/memoria/.gitkeep")
    archivos = [RAIZ / nombre for nombre in nombres if (RAIZ / nombre).is_file()]
    for carpeta in CARPETAS:
        archivos.extend(a for a in (RAIZ / carpeta).rglob("*")
                        if a.is_file() and a.suffix in (".py", ".md") and "__pycache__" not in a.parts)
    DESTINO.parent.mkdir(exist_ok=True)
    with ZipFile(DESTINO, "w", ZIP_DEFLATED) as paquete:
        for archivo in sorted(set(archivos)):
            paquete.write(archivo, "taller-agente-local-ufv/" + archivo.relative_to(RAIZ).as_posix())
    print(DESTINO)


if __name__ == "__main__":
    empaquetar()
