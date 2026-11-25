# Usar el taller desde Claude Code u otro cliente MCP

El servidor MCP expone las mismas búsquedas y cálculo OEE del taller. También
permite delegar una pregunta al agente local con Ollama. Es una integración opcional;
no añade dependencias al arranque normal de los alumnos.

| Herramienta | Qué hace | ¿Necesita Ollama? |
|---|---|---|
| `buscar_apuntes` | Busca en apuntes y memoria Markdown, con rutas y líneas. | No |
| `calcular_oee` | Calcula con la función Python del taller y valida los datos. | No |
| `consultar_tutor_local` | Llama al modelo configurado y le permite buscar y calcular. | Sí |

La delegación devuelve respuesta, modelo, fuentes consultadas y cálculos ejecutados.
Usa los límites del entorno, una conversación nueva por pregunta y la memoria previa
de la bóveda. No puede guardar memoria ni ejecutar comandos. Los resultados del
modelo necesitan revisión. El MCP usa stdio: el cliente inicia el proceso, sin abrir
un puerto ni exponer un servicio a la red.

## Conectar Claude Code

Primero extrae y prepara el taller con `iniciar.cmd` o `bash iniciar.sh preparar`.
Así quedan disponibles uv, Python y el modelo local. Cierra el chat del taller
cuando quieras usar el mismo equipo desde Claude Code.

Desde la carpeta del taller, en Windows:

```powershell
.tools\uv\uv.exe run --python 3.11 --extra mcp python herramientas/conectar_claude.py
```

En macOS/Linux:

```sh
.tools/uv/uv run --python 3.11 --extra mcp python herramientas/conectar_claude.py
```

Se instala el SDK oficial MCP 2.3.0 como dependencia opcional. La primera vez
requiere internet. El comando genera:

- `.mcp.json`: servidor `ufv-local`, con rutas absolutas para este portátil.
- `.claude/agents/tutor-ufv.md`: instrucciones y herramientas del subagente.

Conserva los otros servidores de `.mcp.json`. Si ya existe un `ufv-local` diferente
o un tutor modificado, se detiene sin sustituirlos. En el repositorio del taller,
los archivos generados están excluidos de Git y del ZIP: cada alumno debe generarlos
en su equipo. Si usas otro proyecto, revisa su `.gitignore`. Repite el
proceso si cambias de ubicación y revisa las rutas anteriores si detecta un conflicto.

Abre Claude Code en esa carpeta. Comprueba el servidor con `/mcp` y el subagente
con `/agents`. Claude Code puede pedirte aprobar el servidor del proyecto en una
sesión interactiva. La integración respeta los permisos del cliente.

Prueba estas peticiones:

> Usa tutor-ufv para buscar en mis apuntes el topic MQTT de la maqueta y cita la fuente.

> Pide al tutor local del taller que busque los datos de la Línea Roble y calcule su OEE.

El archivo de subagente organiza un trabajador de **Claude**, con su propio contexto
y las tres herramientas MCP permitidas. Su campo `model: inherit` mantiene el modelo
de Claude Code. La llamada a `consultar_tutor_local` es la que delega realmente al
modelo de **Ollama**. Un archivo Markdown no convierte Claude Code en un cliente
nativo de cualquier modelo local.

Si Ollama no está arrancado, abre el entorno del taller o ejecuta su acción `doctor`
antes de delegar. Búsqueda y OEE directos siguen disponibles sin él. Las consultas
al tutor pueden tardar más que una llamada directa; los límites de espera del cliente
MCP pueden necesitar ajuste según el equipo.

## Usarlo desde otro proyecto

Añade el destino al mismo comando, por ejemplo:

```powershell
.tools\uv\uv.exe run --python 3.11 --extra mcp python herramientas/conectar_claude.py --destino C:\MisProyectos\Asignatura
```

El proyecto de destino debe existir. La bóveda seguirá siendo la del taller; puedes
seleccionar otra carpeta con `--boveda C:\MisApuntes`. Cambiar de bóveda requiere
revisar la entrada existente `ufv-local` antes de regenerarla.

## Otros clientes MCP

El servidor no depende de Claude. La entrada `ufv-local` de `.mcp.json` contiene
`command` y `args` que puedes copiar a la configuración de un cliente MCP compatible
con stdio. Cada cliente puede usar un nombre de archivo o estructura diferente.
El subagente Markdown es específico de Claude Code; el servidor MCP es reutilizable.

Las búsquedas y cálculos se ejecutan en tu ordenador. El cliente recibe los fragmentos
y respuestas: si su modelo usa un servicio remoto, ese contenido puede procesarse allí.
El modo MCP no implica que toda la conversación del cliente sea local.

Para revisar o personalizar las instrucciones, edita
`integraciones/claude/tutor-ufv.md` antes de generar el archivo del proyecto. El servidor
no publica herramientas de escritura; para guardar una nota usa el agente Python
del taller, que presenta la propuesta y pide confirmación.

Referencias: [MCP en Claude Code](https://code.claude.com/docs/en/mcp),
[subagentes de Claude Code](https://code.claude.com/docs/en/sub-agents),
[SDK oficial MCP para Python](https://github.com/modelcontextprotocol/python-sdk).
