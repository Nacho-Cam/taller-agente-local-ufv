# Entorno automático y OpenCode

La versión 0.2 añade un arranque guiado: Python gestionado por uv, Ollama portable,
LFM3 1.7B, OpenCode 2 en modo terminal mínimo y configuración según el equipo.
La primera ejecución necesita internet y varios GB libres; las posteriores reutilizan
las descargas y el modelo. Los instaladores del proyecto verifican los checksums
publicados por los distribuidores. No instalan controladores de GPU.

## Windows

Desde la versión 0.4 puedes usar **Instalar-Taller-UFV.exe**. Descarga y verifica
el paquete del repositorio, lo extrae en tu usuario y ejecuta este mismo arranque.
Consulta [INSTALADOR_WINDOWS.md](INSTALADOR_WINDOWS.md).

Extrae el ZIP completo y abre **iniciar.cmd**. La primera vez instala lo necesario,
detecta el equipo y hace una prueba del modelo; después abre el tutor de OpenCode.
Windows puede pedirte autorizar el lanzamiento de software descargado.

También puedes preparar todo con PowerShell:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\preparar.ps1
```

Acciones disponibles:

```powershell
.\preparar.ps1 -Accion iniciar
.\preparar.ps1 -Accion terminal
.\preparar.ps1 -Accion equipo
.\preparar.ps1 -Accion doctor
.\preparar.ps1 -SoloDetectar
```

Si la política de PowerShell impide ejecutar el archivo, usa la forma larga anterior,
añadiendo `-Accion equipo`, etc. No hace falta cambiar la política del sistema.
`-SoloDetectar` no instala Ollama, OpenCode ni el modelo y no guarda configuración;
el script de arranque sí puede descargar uv/Python para poder realizar la detección.

## macOS y Linux

Desde la carpeta extraída:

```sh
bash iniciar.sh preparar
bash iniciar.sh iniciar
```

Otras acciones: `bash iniciar.sh terminal`, `equipo`, `doctor`.
La instalación soporta x64 y ARM64; el script Linux presupone glibc y `curl`/`tar`.
En Linux instala también el pequeño descompresor Python `zstandard` para el paquete
oficial de Ollama. En todos los sistemas se usa `psutil` para identificar de forma
segura el servidor iniciado por este proyecto.

## Qué se configura

Obsidian 1.15.1 se instala por defecto: instalación de usuario en Windows,
`~/Applications` en macOS y distribución portable oficial en Linux. Una instalación
existente se reutiliza. La primera apertura de `boveda/` requiere elegir **Abrir
carpeta como bóveda**; no se modifican automáticamente las otras bóvedas del usuario.
La acción `notas` abre Obsidian sin arrancar ni preparar el modelo. Con
`-SinObsidian` / `--sin-obsidian` se omite su instalación en el recorrido normal.
Los nuevos recorridos macOS/Linux requieren prueba física; aquí se valida Windows.

| Hardware detectado | Propuesta inicial |
|---|---|
| NVIDIA con al menos 6 GB utilizables | Hasta 3 agentes; contexto 16K. |
| NVIDIA con 4–6 GB utilizables | Hasta 2 agentes; contexto 16K. |
| NVIDIA con 2,5–4 GB utilizables | 1 agente; contexto 8K. |
| Apple Silicon, RAM total de 24 GB o más | Hasta 3 agentes; contexto 16K. |
| Apple Silicon, RAM total de 16 GB | Hasta 2 agentes; contexto 16K. |
| CPU, GPU sin verificar o poca RAM disponible | 1 agente; contexto pequeño. |

Son heurísticas para **LFM3 1.7B Q4**, no límites universales para cualquier modelo.
En NVIDIA se usa la memoria libre actual y se reserva al menos 1 GB de la VRAM total.
En Apple Silicon la memoria es compartida; no se suma a la RAM como si fuera independiente.
Con menos de 4 GB de RAM disponible se propone un único agente y contexto 4K.
Una 5060 Laptop de 8 GB puede recibir un perfil distinto si otras aplicaciones
están usando su memoria.

La preparación carga el modelo, comprueba que produce una llamada a herramienta
y ensaya lotes de una, dos y hasta tres peticiones según el perfil. Reduce la
concurrencia si un lote falla o tarda más que su estimación en serie con un margen
del 35 %. Si no confirma uso de GPU cuando se esperaba, deja un agente.
Esta es una prueba breve de funcionamiento, no un benchmark exhaustivo de agentes
ni una garantía de velocidad o calidad en tareas posteriores.

Los límites quedan en **.local/ajustes.json**, incluyendo resultado y tiempos de
calibración. Repite `preparar` si cambian el equipo, los programas abiertos o los drivers.
No se usa la ventana máxima anunciada de 256K para este taller.

## Un servidor del taller

El lanzador arranca Ollama en un puerto local propio entre 11435 y 11445.
No modifica el Ollama habitual del puerto 11434, el PATH ni las variables globales.
Los ejecutables portables van en `.tools/`; Python y paquetes se gestionan con uv.
El modelo puede quedar en la caché normal de Ollama para no duplicar descargas.
Los ajustes, registros, base de datos de OpenCode y resultados quedan en `.local/`.
Ambas carpetas están excluidas de Git y del ZIP del material.

Solo se mantiene un modelo cargado en el servidor del taller. El número de slots de
inferencia se ajusta con `OLLAMA_NUM_PARALLEL`; las peticiones adicionales esperan
en una cola limitada. El equipo Python aplica además su propio límite de trabajadores.
El número de agentes lógicos abiertos en OpenCode puede ser mayor: estos límites
controlan cuántas inferencias se atienden, no cuántas conversaciones puedes crear.

Si cambias de perfil, el lanzador puede reiniciar su propio servidor. Cierra antes
los chats del taller. Comprueba PID, ejecutable y fecha de creación antes de terminarlo;
no intenta cerrar el servicio de Ollama del usuario.

## OpenCode como tutor

La acción `iniciar` abre **OpenCode 2 Mini**, una interfaz mínima de terminal.
No hace falta instalar Node, npm, T3 ni una aplicación de escritorio.
Se descarga el paquete binario oficial de OpenCode 2 (no el OpenCode 1 de algunas
instrucciones antiguas). Se genera una configuración de tutor que usa solo el proveedor
Ollama local, con acceso a la bóveda y solicitudes de confirmación para editar o ejecutar
comandos. Los buscadores web están deshabilitados en este recorrido.

Prueba «Consulta los apuntes de MQTT y dime qué topic usa la maqueta; cita la fuente».
Después «Recuerda en una nota que quiero repasar OEE» y revisa la escritura propuesta.
Los apuntes son los mismos que usa el agente Python, pero las herramientas de OpenCode
son las suyas: no se presentan como si fueran nuestras funciones Python.

OpenCode recibe más instrucciones y herramientas que el ejemplo mínimo. Un modelo
de 1,7B puede equivocarse al navegar o editar: la prueba de herramientas de Ollama no
demuestra por sí sola que todos los flujos de OpenCode funcionen bien.
Conserva el recorrido `terminal` si la interfaz o el tutor dan problemas.

Antes de seleccionar OpenCode como interfaz, la preparación le pide leer el archivo
MQTT y comprueba tanto la llamada real a `read` como el topic obtenido. Si falla o
supera 180 segundos, `iniciar` abre el agente Python. Los registros quedan en `.local/`.
El razonamiento se desactiva en este recorrido para reducir la espera: `think: false`
en la API nativa y `reasoning_effort: "none"` en OpenCode. Esto no impide encadenar
herramientas. Puedes editar las instrucciones de tutor en `configurar_opencode()`;
la preparación regenera su archivo de configuración.

## Tres tareas en paralelo

La acción `equipo` lanza tres conversaciones independientes sobre MQTT, sensores y OEE.
Comparte el modelo y respeta el número de trabajadores configurado. No permite guardar
memoria desde los trabajadores; así evita peticiones de confirmación simultáneas.
El informe se guarda en `.local/equipo.json`.

Para comparar con la ejecución en serie:

```powershell
.tools\uv\uv.exe run --python 3.11 solucion/equipo.py --secuencial
```

En macOS/Linux, usa `.tools/uv/uv` en lugar de `.tools\uv\uv.exe`.

## T3 como opción posterior

T3 Code admite OpenCode como proveedor, incluido OpenCode 2. Si se quiere una
interfaz de escritorio, se puede añadir después usando el mismo modelo y servidor.
No se instala automáticamente porque añade otra aplicación y configuración a la hora
de taller. La configuración de OpenCode de este proyecto vive en `.local/estudio/`.

Referencias verificadas al preparar el material:

- [OpenCode con Ollama](https://opencode.ai/docs/providers/#ollama).
- [OpenCode Mini y servidor privado](https://opencode.ai/docs/cli/).
- [T3 Code: proveedor OpenCode](https://github.com/pingdotgg/t3code/blob/main/docs/user/providers-opencode.md).
- [Concurrencia y memoria en Ollama](https://docs.ollama.com/faq#how-does-ollama-handle-concurrent-requests).
- [LFM3 y cuantización](https://docs.liquid.ai/examples/agent-harnesses).

## Versiones y recuperación

El material fija uv 0.13.9, Python 3.11, Ollama 0.40.18 y OpenCode 2.4.1.
Un ejecutable de Ollama ya instalado se reutiliza si es 0.40.13 o superior.
Los drivers deben estar instalados y ser compatibles; si fallan, la preparación
mostrará el error y el registro de Ollama. No intenta instalar drivers ni conseguir
permisos de administrador automáticamente.

Si se interrumpe una descarga, vuelve a ejecutar preparar. Las descargas completas
se reutilizan; una descarga parcial se repite. Con `-SinOpenCode` o `--sin-opencode`
puedes preparar solo el taller Python. Con `-SinCalibrar` o `--sin-calibrar` se guarda
un perfil **sin validar**: úsalo únicamente para diagnóstico, no como prueba de capacidad.
