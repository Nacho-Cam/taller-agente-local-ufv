# LFM3 con y sin DSpark

DSpark es un modelo auxiliar de unos 0,3B parámetros para adelantar tokens que
verifica LFM3 1.7B. Se compara el **mismo target** con y sin este auxiliar; no son
dos asistentes con capacidades distintas. El autor anuncia hasta 3,14× en una
A100 de 40 GB, con una petición simultánea. Ese resultado no predice la velocidad
de un portátil ni la de varias conversaciones concurrentes.

Fuentes: [discusión original](https://huggingface.co/LiquidAI/LFM3-1.7B/discussions/29),
[modelo auxiliar GGUF](https://huggingface.co/rasyosef/LFM3-1.7B-DSpark-GGUF),
[target oficial](https://huggingface.co/LiquidAI/LFM3-1.7B-GGUF),
[motor fijado b12681](https://github.com/ggml-org/llama.cpp/releases/tag/b12681).

## Protocolo local

- Windows, RTX 2060 de 6 GB, driver 591.74 y 32 GB de RAM.
- llama.cpp b12681, backend Vulkan, dispositivo NVIDIA seleccionado explícitamente.
  Este portátil también presenta una GPU Intel: no se debe asumir que `Vulkan0`
  corresponde a NVIDIA. El intento CUDA 12.4 tuvo un procesamiento inicial
  anormalmente lento y se interrumpió; no aporta resultados comparables.
- Targets LFM3 Q4_K_M y Q8_0, auxiliar DSpark Q8_0. Revisiones y SHA256 fijados en
  `herramientas/preparar_benchmark.py` y en los informes JSON.
- Q4 explora bloques máximos de 2, 4 y 8 tokens; Q8 compara el bloque de 4 con su
  propia referencia. Una confirmación adicional Q4 repite referencia y bloque de 4.
  Todos con la misma
  plantilla, instrucciones, muestreo y límites: temperatura 0,1, top-k 50, top-p 1,
  min-p 0, penalización de repetición 1,1; razonamiento desactivado y salida de 256 tokens.
- Tres slots, 12.288 tokens totales, 4096 por slot. La carga y una consulta de
  calentamiento quedan fuera de los tiempos. La confirmación Q4 añade una batería
  completa en serie y paralelo antes de cada medición. Caché de prompt desactivada.
- Cuatro consultas en serie: explicación industrial en español, código en inglés,
  selección de búsqueda y llamada OEE con sus cinco argumentos. Después, las tres
  primeras se envían simultáneamente. Dos repeticiones invierten el orden de las
  configuraciones; las semillas son 42 y 43.
- Se registran duración completa, tokens generados, velocidad de generación,
  tokens propuestos/aceptados, respuestas, llamadas y argumentos OEE. La memoria
  GPU es una fotografía del total ocupado, no un máximo ni memoria exclusiva del proceso.

Las comprobaciones automáticas verifican contenido no vacío y estructura de las
dos herramientas; no puntúan la corrección general del texto o del código. Una
salida cortada a 256 tokens tampoco equivale a un ejercicio resuelto. Las respuestas
pueden tener distinta longitud: hay que leer juntos latencia y tokens por segundo.
Esto es una prueba pequeña del recorrido, no una clasificación general de modelos.
El ensayo completo de búsqueda, memoria y OEE con Ollama está en [VALIDACION.md](VALIDACION.md).

## Confirmación con calentamiento completo

Cada configuración ejecuta una batería completa en serie y paralelo antes de medir.
La velocidad agrupa los tokens y tiempos de ambas repeticiones; las duraciones son medias.
Q4 completó ambas repeticiones el 24 de noviembre. Q8 se repitió el 25: solo su
primera pareja terminó, porque DSpark se bloqueó durante el segundo lote paralelo.

| Target | Auxiliar | Español (tokens/s) | Código (tokens/s) | Cuatro consultas (s) | Lote paralelo (s) |
|---|---|---:|---:|---:|---:|
| Q4 | Sin DSpark | 99,57 | 97,80 | 7,09 | 4,65 |
| Q4 | DSpark, bloque 4 | 48,90 | 73,96 | 10,77 | 7,20 |

En Q8, la única pareja completa tardó **9,34 s sin auxiliar frente a 12,91 s con
DSpark** en las cuatro consultas; el paralelo tardó 4,47 frente a 7,09 s. No se
calculan medias de dos repeticiones para Q8. La segunda ejecución DSpark dejó de
avanzar tras completar una de las tres peticiones paralelas y se interrumpió
terminando el proceso propio. El JSON marca `incompleto_por_bloqueo`; no se atribuye
el fallo a un componente concreto sin un diagnóstico adicional. No se siguió
usando la GPU para repetir esa configuración.

En Q4, el bloque de 4 **aumenta la espera** aproximadamente un 52 % en serie y
un 55 % en paralelo. Las dos repeticiones mantienen esa dirección. No hay evidencia
para añadir esta configuración al arranque automático del taller. No es un resultado
de Ollama ni una predicción para la 5060: ambos lados usan el mismo llama.cpp/Vulkan
en la RTX 2060. Otros bloques, backends, tareas o GPUs pueden dar otro resultado.

Los informes y el ZIP se adjuntan a la [versión 0.2.0](https://github.com/Nacho-Cam/taller-agente-local-ufv/releases/tag/v0.2.0).
El script conserva los errores, limita las esperas de inferencia y del diagnóstico
NVIDIA, y devuelve un código de error si alguna configuración falla.

## Exploración inicial: calentamiento insuficiente

Velocidad de generación agrupada por tokens y tiempo de las dos repeticiones;
duración media de las cuatro consultas en serie y del lote de tres en paralelo.
Estos números se conservan para documentar el problema de medición; **no se usan
para elegir modelo ni calcular las mejoras de la conclusión**. La confirmación anterior
incluye el calentamiento completo que faltaba en esta exploración.

| Target | Auxiliar | Español (tokens/s) | Código (tokens/s) | Cuatro consultas (s) | Lote paralelo (s) |
|---|---|---:|---:|---:|---:|
| Q4 | Sin DSpark | 22,39 | 22,13 | 30,76 | 9,68 |
| Q4 | DSpark, bloque 2 | 18,42 | 27,09 | 29,65 | 20,52 |
| Q4 | DSpark, bloque 4 | 17,87 | 27,34 | 29,03 | 19,20 |
| Q4 | DSpark, bloque 8 | 16,98 | 23,77 | 32,03 | 25,23 |
| Q8 | Sin DSpark | 67,39 | 68,27 | 9,87 | 6,57 |
| Q8 | DSpark, bloque 4 | 42,54 | 60,02 | 12,58 | 7,23 |

El paralelo sin auxiliar varió bastante: Q4, 13,97 y 5,39 s; Q8, 8,44 y 4,70 s.
Una consulta corta de calentamiento no garantiza calentar todas las rutas y shaders.
Solo hay dos repeticiones: no corresponde interpretar las medias como una estimación
precisa de ganancia. Los JSON conservan tiempos, tokens y resultados individuales.
En Q8 DSpark redujo la velocidad de generación en español y código en ambas
repeticiones. Los beneficios aparentes de Q4 en código no se mantuvieron al repetir
con calentamiento completo; no fundamentan la elección del entorno.

La inspección de las primeras respuestas Q4 detectó errores de concepto sobre QoS,
referencias a una memoria personal que no se había proporcionado y menciones de OEE
fuera de la pregunta. Aparecen problemas tanto con auxiliar como sin él. Un resultado
`comprobacion_basica: true` solo valida el criterio limitado descrito, no una respuesta
correcta para entregar a un alumno. Para enseñar contenidos, conviene trabajar con
los apuntes preparados, revisar las fuentes y contrastar la respuesta.

## Repetir en Windows

Es opcional y descarga varios GB adicionales. Cierra los chats y descarga de GPU
otros modelos antes de medir. No forma parte del arranque normal de alumnos.

```powershell
.tools\uv\uv.exe run --python 3.11 herramientas/preparar_benchmark.py --incluir-q8
.tools\benchmark\llama-b12681-vulkan\llama-server.exe --list-devices
```

Sustituye `Vulkan1` por el identificador NVIDIA que muestre tu equipo:

```powershell
.tools\uv\uv.exe run --python 3.11 herramientas/benchmark_dspark.py --server .tools/benchmark/llama-b12681-vulkan/llama-server.exe --target .tools/benchmark/LFM3-1.7B-Q4_K_M.gguf --draft .tools/benchmark/LFM3-1.7B-DSpark-Q8_0.gguf --device Vulkan1 --bloques 0 4 --salida dist/benchmark-dspark-q4-confirmacion.json
```

Para Q8, cambia el target a `LFM3-1.7B-Q8_0.gguf` y usa
`dist/benchmark-dspark-q8-confirmacion.json` como informe. El calentamiento completo
es el comportamiento predeterminado. `--bloques 0 2 4 8` amplía la exploración;
`--calentamiento-breve` reproduce el método inicial, con sus limitaciones.
No ejecutes benchmarks a la vez.
El script inicia un servidor propio en localhost:11590 y lo termina al acabar.
Se puede usar otro binario de llama-server mediante `--server`; sus resultados
deben etiquetarse con ese motor y backend y compararse con su propia referencia.
