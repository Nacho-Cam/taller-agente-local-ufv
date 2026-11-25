# Tu primer agente local · UFV

Taller de una hora para Ingeniería de la Industria Conectada.
Construye un asistente que consulta apuntes, guarda memoria entre sesiones y usa
una función de Python para calcular el OEE de una línea ficticia.

El tutor también gestiona la carrera: crea cursos y asignaturas, organiza temas,
apuntes, tareas y exámenes, importa PDFs con texto y muestra lo pendiente por fecha.
Los cambios aparecen en Obsidian en `Carrera.md`. [Uso académico y herramientas](docs/CARRERA.md).

**Ollama + Python + archivos Markdown**, con OpenCode Desktop o terminal a elegir.
Sin claves API ni Docker. Obsidian se incluye para ver y editar las notas. La práctica no se conecta a Canvas.

## Arranque automático recomendado

Descarga el instalador de tu sistema de [la versión actual](https://github.com/Nacho-Cam/taller-agente-local-ufv/releases/latest):
**EXE para Windows**, **aplicación para macOS** (Apple Silicon o Intel) o **ejecutable para Linux x64**.
La ventana permite elegir OpenCode Desktop, Obsidian, CLI y calibración, cambiar la carpeta
y seguir el progreso. Guarda la elección y deja un acceso **Taller UFV** en tu usuario.
No necesitas instalar Python antes. [Instalación, carpetas y actualizaciones](docs/INSTALACION.md).

También puedes descargar el ZIP y extraerlo completo:

- **Windows:** abre `iniciar.cmd`.
- **macOS/Linux:** abre una terminal en la carpeta y ejecuta `bash iniciar.sh`.

La primera ejecución desde el ZIP prepara Python, instala Obsidian en tu usuario y Ollama y OpenCode en el proyecto si
hacen falta, descarga **LFM3 1.7B**, detecta memoria/GPU y prueba la concurrencia.
Pregunta si quieres **instalar y usar la aplicación de escritorio de OpenCode** o
**usar solo la terminal**. Guarda esa elección en `.local/interfaz.json`.
Después abre Obsidian directamente en `boveda/Inicio.md` y el tutor en OpenCode.
La carpeta del taller queda registrada automáticamente como bóveda.
El tutor conoce las rutas de apuntes, memoria y documentación. El arranque conecta
las herramientas MCP de búsqueda y cálculo de OEE, y comprueba que responden.
Desktop abre la carpeta del taller con todos sus materiales visibles. El EXE deja
un acceso **Taller UFV** en el menú Inicio para arrancar modelo, notas y tutor juntos.
Hazlo antes de clase: necesita internet,
varios GB de descargas y al menos 7 GB libres para preparar el entorno.

Los límites se guardan en `.local/ajustes.json`. La propuesta va de uno a tres agentes;
se valida con una prueba breve y se reduce si falla. NVIDIA y Apple Silicon tienen
perfiles; GPU desconocida o memoria escasa reciben un perfil CPU conservador.
No se instalan drivers ni se modifica el Ollama habitual del usuario.

En Windows puedes lanzar también:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\preparar.ps1 -Accion terminal
powershell -NoProfile -ExecutionPolicy Bypass -File .\preparar.ps1 -Accion equipo
powershell -NoProfile -ExecutionPolicy Bypass -File .\preparar.ps1 -Accion notas
```

`terminal` abre nuestro agente Python para el taller. `equipo` ejecuta tres tareas
independientes con el límite configurado. [Detalles, perfiles y recuperación](docs/ENTORNO.md).
El arranque gestiona `psutil` y, en Linux, `zstandard`; el agente mínimo usa la biblioteca estándar.
Para omitir Obsidian en un equipo sin escritorio, usa `-SinObsidian` en PowerShell
o `--sin-obsidian` en el lanzador Bash. [Detalles del EXE](docs/INSTALADOR_WINDOWS.md).

Para cambiar de interfaz desde el ZIP, vuelve a ejecutar el lanzador con `--ui elegir`, o usa
`--ui si` para Desktop y `--ui no` para la terminal. Desde el repositorio:

```powershell
.\preparar.ps1 -Accion iniciar -UI elegir
```

En macOS/Linux: `bash iniciar.sh iniciar --ui elegir`. Sin entrada interactiva,
el arranque usa terminal salvo que haya una elección guardada o se indique `--ui si`.
Elegir terminal no desinstala una app que ya tengas. La CLI sigue disponible en ambas opciones.

## Instalación manual alternativa

Si prefieres preparar tú los programas, este recorrido conserva el modelo Qwen
de la primera versión. Si ya has ejecutado el arranque automático, los programas
Python toman por defecto su modelo, dirección y límites de `.local/ajustes.json`.

1. Instala [Python](https://www.python.org/downloads/) 3.9 o superior (recomendado 3.11+).
   En Windows, activa la opción de añadir Python al PATH, si aparece.
2. Instala y abre [Ollama](https://ollama.com/download).
3. Descarga el modelo **antes de clase** desde una terminal:

   ```sh
   ollama pull qwen3:4b-instruct
   ```

La descarga del modelo ronda 2,5 GB; necesita memoria adicional al ejecutarse.
Como orientación para este taller, empieza con 16 GB de RAM o más y espacio libre
para Ollama y el modelo. No es una garantía de velocidad: ejecuta el diagnóstico
y una pregunta en tu portátil. Hay una alternativa de menor tamaño más abajo.
Con las descargas terminadas, el programa usa únicamente Ollama en `127.0.0.1`.

## Descarga y arranque

Usa **Code → Download ZIP** en este repositorio y extrae la carpeta, o clónalo:

```sh
git clone https://github.com/Nacho-Cam/taller-agente-local-ufv.git
cd taller-agente-local-ufv
```

Abre una terminal dentro de la carpeta extraída o clonada. En Windows:

```powershell
py solucion/agente.py --doctor --modelo qwen3:4b-instruct
py solucion/agente.py --modelo qwen3:4b-instruct
```

En macOS y Linux:

```sh
python3 solucion/agente.py --doctor --modelo qwen3:4b-instruct
python3 solucion/agente.py --modelo qwen3:4b-instruct
```

El diagnóstico verifica conexión, modelo y soporte declarado de herramientas;
una pregunta comprueba además la inferencia. Prueba:

> Busca los datos de la Línea Roble en mis apuntes y calcula su OEE usando la herramienta.

Debe mostrar llamadas a `buscar_apuntes` y `calcular_oee`. El OEE de referencia es
**67,8571 %**. La traza muestra qué funciones se ejecutan realmente.

## Dos recorridos

| Carpeta | Para qué sirve |
|---|---|
| `plantilla/` | Completar tres TODO siguiendo [la guía de alumnos](docs/ALUMNOS.md). |
| `solucion/` | Ejemplo terminado para probar, comparar y continuar si te atascas. |

Las dos versiones usan `nucleo.py` y la misma `boveda/`. No copies solamente
`agente.py`: conserva la estructura del repositorio.

- [Guía de alumnos y retos](docs/ALUMNOS.md)
- [Preparación y guion del ponente](docs/PONENTE.md)
- [Mensaje previo para los alumnos](docs/PREPARACION.md)
- [Opciones de memoria, PDF y Canvas](docs/DECISIONES.md)
- [Registro de validación](docs/VALIDACION.md)
- [Comparación de rendimiento con DSpark](docs/BENCHMARK_DSPARK.md)
- [Conectar como MCP y subagente de Claude Code](docs/MCP_Y_CLAUDE.md)
- [Entorno automático, OpenCode y concurrencia](docs/ENTORNO.md)

## Memoria que puedes abrir

```text
boveda/
  Inicio.md
  apuntes/       ← documentos .md que tú añades
  memoria/       ← notas que autorizas guardar
```

El arranque abre `boveda` en [Obsidian](https://obsidian.md/) automáticamente.
También puedes usar cualquier editor. No necesitas plugins ni una cuenta.

Pide «Recuerda que quiero repasar OEE con ejemplos de fabricación». El programa
te muestra la nota y pregunta si quieres guardarla. Confirma con `s`.
Usa `/nuevo` o cierra y vuelve a abrir; las cuatro últimas notas se cargan desde disco.
Las anteriores siguen disponibles mediante la herramienta de búsqueda.
`/salir` termina. El historial de conversación vive en RAM y se descarta al cerrar.

Los archivos personales de `memoria/` están excluidos de Git. No publiques apuntes
privados al personalizar el repositorio: Git sí incluye `apuntes/`.

## Si algo falla

| Problema | Qué probar |
|---|---|
| `py` no existe | Prueba `python` en Windows; `python3` en macOS/Linux. |
| Ollama no responde | Abre la aplicación, o ejecuta `ollama serve` en otra terminal. |
| Falta el modelo | Ejecuta `ollama pull qwen3:4b-instruct`. |
| Error con herramientas | Actualiza Ollama y repite `--doctor`. |
| Va muy lento | Cierra otras aplicaciones, usa preguntas cortas o prueba el modelo menor. |
| La plantilla inventa respuestas | Aún no tiene herramientas conectadas: completa los TODO y observa la traza. |
| No encuentra un concepto | Busca palabras presentes en el documento; esta búsqueda no entiende sinónimos. |
| PDF no aparece en búsqueda | Esta versión lee solo Markdown. Lleva un texto breve convertido previamente. |

Alternativa ligera, que también debes ensayar porque puede usar peor las herramientas:

```sh
ollama pull qwen3:1.7b
```

```powershell
py solucion/agente.py --modelo qwen3:1.7b
```

Si no funciona la inferencia, puedes estudiar la búsqueda sin modelo:

```powershell
py solucion/agente.py --buscar "OEE Roble"
```

La salida anterior es una búsqueda determinista; no simula una respuesta del modelo.

## Comprobaciones del proyecto

```sh
python -m unittest discover -s tests -v
python herramientas/empaquetar.py
```

En Windows puedes sustituir `python` por `py`; en macOS/Linux, por `python3`.
El empaquetador crea `dist/taller-agente-local-ufv.zip` sin memoria personal,
configuración de Obsidian ni cachés. Las pruebas automáticas no necesitan Ollama.
El ensayo con modelo real se registra aparte en `docs/VALIDACION.md`.
