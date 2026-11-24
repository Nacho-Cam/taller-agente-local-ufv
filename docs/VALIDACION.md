# Validación · 24 de noviembre de 2026

## Pruebas del programa

Python 3.9.6, Windows, sin paquetes externos: **8 pruebas correctas**.
Cubren búsqueda con acentos y ausencia de resultados, escritura cancelada,
persistencia y recarga de memoria, OEE y datos inconsistentes, herramientas permitidas,
devolución de resultados y errores al modelo, y límite del bucle.
En las pruebas del bucle las respuestas del modelo son simuladas.

## Ensayo con modelo local real

Ejecutado con `qwen3:4b-instruct` (identificador local `0edcdef34593`), contexto de
8192 tokens, `think: false`, Windows, 32 GB de RAM y NVIDIA RTX 2060.
El modelo estaba cargado en GPU. Los tiempos siguientes son de este equipo y
con el modelo caliente; no incluyen la descarga ni garantizan tiempos en otros portátiles.

| Caso | Observación real | Tiempo |
|---|---|---|
| Consulta MQTT | Usó `buscar_apuntes`; devolvió el topic correcto con ruta y líneas. | 2,22 s |
| Guardar memoria | Usó `guardar_memoria`; creó una nota en la bóveda temporal. | 2,17 s |
| Recuperar memoria | Una conversación nueva recuperó el objetivo OEE desde disco. | 0,94 s |
| OEE | Encadenó búsqueda y cálculo; la función devolvió 67,8571 % y el modelo lo redondeó a 67,86 %. | 6,72 s |
| Dato ausente | Buscó y reconoció que no está especificada la frecuencia de calibración del sensor. | 3,19 s |

El ensayo se ejecuta con `python herramientas/ensayo.py`. Usa una bóveda temporal
y acepta automáticamente solo la nota ficticia de su caso de memoria. La aplicación
normal sigue pidiendo confirmación por consola. El informe completo queda en
`dist/ensayo-real.json` y se adjunta a la versión publicada.

Se corrigió un fallo de salida Unicode en la consola de Windows detectado durante
el primer ensayo. Después se completaron los cinco casos.

## Límites observados y comprobaciones pendientes

- En OEE el modelo no siempre incluye la cita final, aunque haya consultado el documento.
- En el caso del sensor citó también un fragmento de MQTT que no aporta la frecuencia
  de calibración. La búsqueda léxica puede devolver fragmentos irrelevantes.
- El ensayo comprueba el recorrido y permite inspeccionar las respuestas; no es una
  evaluación exhaustiva de calidad ni garantiza que siempre llame las herramientas.
- `qwen3:1.7b`, macOS y Linux no se han ensayado aquí.
- No se han probado los portátiles de los alumnos, el wifi de la universidad ni Canvas.
- Hace falta el ensayo del ponente con su explicación, tiempos de instalación y material final.
