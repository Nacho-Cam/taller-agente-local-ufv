"""Solución: observa cómo el programa ejecuta lo que pide el modelo."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nucleo import HERRAMIENTAS, MAX_LLAMADAS, MAX_RONDAS, chat, ejecutar_herramienta, iniciar


def resolver_turno(mensajes, modelo, boveda, herramientas=None, ejecutar=None):
    herramientas = HERRAMIENTAS if herramientas is None else herramientas
    ejecutar = ejecutar_herramienta if ejecutar is None else ejecutar
    llamadas = 0
    for _ in range(MAX_RONDAS):
        mensaje = chat(mensajes, modelo, herramientas)
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
                resultado = ejecutar(nombre, argumentos, boveda)
            except (ValueError, TypeError, OSError) as error:
                resultado = {"error": str(error)}
            mensajes.append({"role": "tool", "tool_name": nombre,
                             "content": json.dumps(resultado, ensure_ascii=False)})
    print('  [límite] Se solicita una respuesta final con la información ya recuperada.')
    mensajes.append({'role': 'user', 'content': 'Responde ahora a mi petición con los resultados disponibles. No hagas más búsquedas ni cálculos. Si falta información, dilo.'})
    final = chat(mensajes, modelo, [])
    mensajes.append(final)
    if final.get('tool_calls') or not final.get('content'):
        raise RuntimeError('El agente agotó sus rondas sin producir una respuesta final. Usa /nuevo para continuar.')
    return final['content']


if __name__ == "__main__":
    sys.exit(iniciar(resolver_turno))
