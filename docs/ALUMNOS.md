# Práctica de 60 minutos

Meta: explicar y ejecutar el ciclo **pregunta → modelo → herramienta → resultado → modelo**.
Al terminar, debes poder distinguir la respuesta del modelo de un resultado calculado
y comprobar qué queda guardado cuando cierras el programa.

Antes de clase, completa el [arranque automático](ENTORNO.md). OpenCode sirve como
interfaz de tutor; durante esta práctica abrirás el agente Python para ver y cambiar
su bucle. Si Python no está en tu PATH, sustituye `py` en los comandos de esta guía
por `.tools\uv\uv.exe run --python 3.11`. En macOS/Linux usa
`.tools/uv/uv run --python 3.11`.

## 0–5 min · Comprueba el equipo

Desde la raíz del repositorio:

```powershell
py solucion/agente.py --doctor
```

En macOS/Linux usa `python3` en lugar de `py` en todos los comandos.
Si te falta una descarga o el equipo falla, trabaja por parejas con un portátil preparado.

## 5–12 min · Primera conversación

```powershell
py plantilla/agente.py
```

Pregunta «¿Qué topic MQTT hemos elegido en nuestra maqueta?».
La plantilla todavía no ofrece herramientas. Aunque produzca una respuesta convincente,
no ha consultado tus apuntes. Abre `boveda/apuntes/MQTT.md` y compruébalo.

En el código, localiza el mensaje de usuario, la llamada a Ollama y la respuesta.
El modelo es un componente: el programa que lo rodea decide qué puede hacer.

## 12–25 min · Conecta herramientas

Abre `plantilla/agente.py` en tu editor y completa estos tres TODO:

1. Ofrece `HERRAMIENTAS` en lugar de `[]` en la llamada a `chat`.
2. Sustituye el resultado provisional por `ejecutar_herramienta(nombre, argumentos, boveda)`.
3. Añade el resultado a `mensajes` con este formato:

   ```python
   mensajes.append({
       "role": "tool",
       "tool_name": nombre,
       "content": json.dumps(resultado, ensure_ascii=False),
   })
   ```

Guarda, cierra el programa y vuelve a ejecutarlo para cargar los cambios.
Pregunta «Busca en mis apuntes qué topic MQTT usa nuestra maqueta y cita la fuente».
Comprueba que aparece `[herramienta] buscar_apuntes`.
Compara con `solucion/agente.py` si te atascas más de tres minutos.

## 25–35 min · Añade conocimiento propio

Crea `boveda/apuntes/Mi-asignatura.md` con 10–20 líneas sobre un concepto que conozcas.
Incluye un dato reconocible que el modelo no pueda deducir: por ejemplo,
«En nuestra maqueta el sensor se llama Faro-27 y se consulta cada 7 segundos».
Pide al agente buscarlo y citar la ruta. No hace falta reiniciar para buscar archivos nuevos.

Prueba una pregunta que el documento no responda. ¿Lo reconoce? Una instrucción
de no inventar ayuda, pero no garantiza que el modelo la cumpla.
La búsqueda compara palabras normalizadas, sin embeddings ni comprensión de sinónimos.

## 35–45 min · Memoria entre sesiones

1. Pide «Recuerda que quiero practicar OEE con ejemplos de fabricación».
2. Comprueba la nota propuesta y confirma con `s` si es correcta.
3. Abre el archivo creado en `boveda/memoria/`, con tu editor o con Obsidian.
4. Sal con `/salir`, vuelve a arrancar y pregunta «¿Qué quería practicar?».
5. Edita esa nota, usa `/nuevo` y comprueba que el cambio se carga.

Pregunta de control: ¿hemos entrenado el modelo? No: guardamos texto y lo volvemos
a incluir en su contexto. La persistencia la proporciona el programa y el disco.

## 45–55 min · Una herramienta de ingeniería

Pide «Busca los datos de la Línea Roble en mis apuntes y calcula su OEE usando la herramienta».
Observa si encadena búsqueda y cálculo. Si no lo hace, divide la petición en dos turnos:
primero los datos y luego el cálculo. También puedes probar con los datos explícitos:

> Calcula con calcular_oee: 420 minutos planificados, 360 en marcha, 600 piezas
> totales, 570 buenas y ciclo ideal de 30 segundos por pieza.

OEE esperado: 67,8571 %. El cálculo lo hace Python. La explicación la escribe el modelo.
Prueba datos inconsistentes: 650 piezas buenas sobre 600. ¿Qué devuelve la función?

## 55–60 min · Explica lo que has construido

Por parejas, enseñad una búsqueda, una nota persistente y una llamada a herramienta.
Cada integrante debe poder explicar qué hace el modelo y qué hace Python.

Retos para continuar:

- Ejecuta `solucion/equipo.py` para ver tres tareas independientes con el límite
  detectado. Compara con `--secuencial`: ¿mejora el tiempo total?
- Modifica las instrucciones para pedirte primero un intento de solución.
- Implementa una conversión de 4–20 mA a presión para el sensor ficticio de los apuntes.
  Añade su esquema a `HERRAMIENTAS` y su ejecución a `ejecutar_herramienta`.
- Haz que la búsqueda ordene mejor los resultados o acepte sinónimos.
- Lee `docs/DECISIONES.md` para pensar una integración con Canvas.
