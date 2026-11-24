"""Solución: observa cómo el programa ejecuta lo que pide el modelo."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nucleo import HERRAMIENTAS, MAX_LLAMADAS, MAX_RONDAS, chat, ejecutar_herramienta, iniciar


def resolver_turno(mensajes, modelo, boveda):
    llamadas = 0
    for _ in range(MAX_RONDAS):
        mensaje = chat(mensajes, modelo, HERRAMIENTAS)
        mensajes.append(mensaje)
        solicitudes = mensaje.get("tool_calls", [])
        if not solicitudes:
            return mensaje.get("content") or "El modelo no produjo una respuesta. Prueba una pregunta más concreta."
        if llamadas + len(solicitudes) > MAX_LLAMADAS:
            raise RuntimeError("Se alcanzó el límite de herramientas. Prueba una petición más sencilla.")
        for solicitud in solicitudes:
            llamadas += 1
            funcion = solicitud["function"]
            nombre = funcion["name"]
            argumentos = funcion.get("arguments", {})
            print(f"  [herramienta] {nombre}: {json.dumps(argumentos, ensure_ascii=False)}")
            try:
                resultado = ejecutar_herramienta(nombre, argumentos, boveda)
            except (ValueError, TypeError, OSError) as error:
                resultado = {"error": str(error)}
            mensajes.append({"role": "tool", "tool_name": nombre,
                             "content": json.dumps(resultado, ensure_ascii=False)})
    raise RuntimeError("El agente agotó sus rondas. Las notas confirmadas ya están guardadas; usa /nuevo para continuar.")


if __name__ == "__main__":
    sys.exit(iniciar(resolver_turno))
