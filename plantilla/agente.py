"""Completa los tres TODO siguiendo docs/ALUMNOS.md."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nucleo import HERRAMIENTAS, MAX_LLAMADAS, MAX_RONDAS, chat, ejecutar_herramienta, iniciar


def resolver_turno(mensajes, modelo, boveda):
    llamadas = 0
    for _ in range(MAX_RONDAS):
        # TODO 1: sustituye [] por HERRAMIENTAS para que el modelo sepa qué puede pedir.
        mensaje = chat(mensajes, modelo, [])
        mensajes.append(mensaje)
        solicitudes = mensaje.get("tool_calls", [])
        if not solicitudes:
            return mensaje.get("content") or "El modelo no produjo una respuesta. Prueba una pregunta más concreta."
        if llamadas + len(solicitudes) > MAX_LLAMADAS:
            raise RuntimeError("Se alcanzó el límite de herramientas.")
        for solicitud in solicitudes:
            llamadas += 1
            funcion = solicitud["function"]
            nombre = funcion["name"]
            argumentos = funcion.get("arguments", {})
            print(f"  [herramienta] {nombre}: {json.dumps(argumentos, ensure_ascii=False)}")
            try:
                # TODO 2: llama a ejecutar_herramienta(nombre, argumentos, boveda).
                resultado = {"error": "Herramienta aún sin conectar en la plantilla"}
            except (ValueError, TypeError, OSError) as error:
                resultado = {"error": str(error)}
            # TODO 3: devuelve el resultado al modelo con mensajes.append(...).
            # Debe incluir role='tool', tool_name=nombre y content=json.dumps(resultado, ensure_ascii=False).
    raise RuntimeError("El agente agotó sus rondas. Revisa los TODO o abre la solución.")


if __name__ == "__main__":
    sys.exit(iniciar(resolver_turno))
