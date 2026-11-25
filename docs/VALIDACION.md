# Validación · 24 de noviembre de 2026

## Versión 0.2: entorno automático y LFM3

Windows, Python gestionado 3.11.18, 32 GB RAM, RTX 2060 de 6 GB y driver 591.74.
Ollama portable 0.40.18, OpenCode 2.4.1 y `lfm3:1.7b-q4_K_M`, con contexto 16K,
700 tokens máximos de salida y razonamiento desactivado.

- **19 pruebas automáticas correctas**: incluyen perfiles simulados de hardware,
  límites compartidos de concurrencia, reducción tras fallos de calibración,
  protección de rutas al extraer y cierre del bucle con una respuesta sin herramientas.
- Calibración caliente: una petición 0,73 s; lote de dos 0,95 s. Se verificó uso
  de GPU mediante Ollama. El perfil quedó limitado a dos inferencias simultáneas.
- Lectura real desde OpenCode: llamó a `read` y recuperó el topic correcto en 9,23 s.
  No equivale a validar todos los flujos de edición o memoria de OpenCode.
- Tres conversaciones Python independientes completadas con dos trabajadores:
  MQTT, sensores y OEE; lote total 31,98 s.
- Ensayo final Python: cinco casos completados con herramientas reales y bóveda temporal.

| Caso LFM3 | Tiempo caliente | Comprobación |
|---|---:|---|
| MQTT | 5,02 s | Topic correcto y cita de archivo/líneas. |
| Guardar memoria | 8,38 s | Nota ficticia guardada tras confirmación del ensayo. |
| Recuperar tras reiniciar conversación | 4,64 s | Recuperó OEE y fabricación desde la nota. |
| OEE | 13,92 s | Dos búsquedas y cálculo determinista: 67,8571 %. |
| Dato ausente | 5,59 s | Reconoció que falta el intervalo de calibración. |

La primera carga fría observada necesitó 155 s; se excluye de los tiempos calientes.
Descargas e inicialización deben hacerse antes de la clase. LFM3 puede repetir una
búsqueda, omitir una cita o redactar una nota más larga de lo pedido. El programa
limita rondas y devuelve los cálculos a una función Python para evitar delegar la aritmética.

El perfil de 5060 Laptop y los de Apple Silicon se comprobaron con datos simulados,
sin esos equipos físicos. macOS/Linux solo tienen revisión del código y sintaxis del
lanzador Bash; requieren ensayo en un equipo real antes de prometer compatibilidad.

La comparación opcional con DSpark se ejecutó los días 24 y 25 de noviembre,
usando un motor separado de Ollama. El [protocolo y sus limitaciones](BENCHMARK_DSPARK.md)
distinguen la exploración inicial de las mediciones con calentamiento completo.

## Versión 0.1: referencia histórica con Qwen

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
