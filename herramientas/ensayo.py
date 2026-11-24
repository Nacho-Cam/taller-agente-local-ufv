"""Ensayo con Ollama real en una bóveda temporal. No modifica tus notas."""
import contextlib
import io
import json
import shutil
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import nucleo
from solucion import agente


def ensayar():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    informe = {"fecha": datetime.now().astimezone().isoformat(timespec="seconds"),
               "modelo": nucleo.MODELO, "casos": []}
    with tempfile.TemporaryDirectory() as temporal:
        boveda = Path(temporal) / "boveda"
        shutil.copytree(nucleo.BOVEDA / "apuntes", boveda / "apuntes")
        casos = [
            ("busqueda", "Busca en mis apuntes qué topic MQTT usamos en nuestra maqueta y cita la fuente.", ["buscar_apuntes"]),
            ("memoria", "Recuerda que quiero practicar OEE con ejemplos de fabricación. Guárdalo en mi memoria.", ["guardar_memoria"]),
            ("recuperacion", "¿Qué quiero practicar según tu memoria previa?", []),
            ("oee", "Busca los datos de la Línea Roble en mis apuntes y calcula su OEE usando la herramienta.", ["buscar_apuntes", "calcular_oee"]),
            ("dato_ausente", "Busca en mis apuntes cada cuánto hay que calibrar el sensor P-101. ¿Está especificado?", ["buscar_apuntes"]),
        ]
        for nombre, pregunta, esperadas in casos:
            mensajes = nucleo.nuevos_mensajes(boveda) + [{"role": "user", "content": pregunta}]
            inicio = time.monotonic()
            captura = io.StringIO()
            # En el ensayo aceptamos únicamente la nota de ejemplo del caso memoria.
            # El chat y todas las llamadas al modelo son reales, sin simulación.
            original = agente.ejecutar_herramienta

            def ejecutar(nombre_herramienta, argumentos, raiz):
                return original(nombre_herramienta, argumentos, raiz,
                                confirmar=lambda _: "s" if nombre == "memoria" else "n")

            try:
                with contextlib.redirect_stdout(captura), patch.object(agente, "ejecutar_herramienta", side_effect=ejecutar):
                    respuesta = agente.resolver_turno(mensajes, nucleo.MODELO, boveda)
                herramientas = [m["tool_name"] for m in mensajes if m["role"] == "tool"]
                caso = {"nombre": nombre, "segundos": round(time.monotonic() - inicio, 2),
                        "herramientas": herramientas, "herramientas_esperadas_presentes": all(h in herramientas for h in esperadas),
                        "respuesta": respuesta, "traza": captura.getvalue(),
                        "resultados_herramientas": [json.loads(m["content"]) for m in mensajes if m["role"] == "tool"]}
            except Exception as error:
                caso = {"nombre": nombre, "segundos": round(time.monotonic() - inicio, 2), "error": str(error), "traza": captura.getvalue()}
            informe["casos"].append(caso)
            destino = nucleo.RAIZ / "dist" / "ensayo-real.json"
            destino.parent.mkdir(exist_ok=True)
            destino.write_text(json.dumps(informe, ensure_ascii=False, indent=2), encoding="utf-8")
            print(json.dumps(caso, ensure_ascii=False), flush=True)
    return 1 if any("error" in c or not c.get("herramientas_esperadas_presentes", False) for c in informe["casos"]) else 0


if __name__ == "__main__":
    sys.exit(ensayar())
