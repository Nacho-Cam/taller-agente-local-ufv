# Instalador EXE de Windows

**Desde la versión 0.7 el EXE tiene interfaz gráfica y guarda la instalación en una carpeta estable. Consulta [Instalación y actualizaciones](INSTALACION.md) para la versión actual.**

El resto de este documento describe el arranque de consola de las versiones 0.6 y anteriores, conservado en `herramientas/instalador_windows.py`. Sus indicadores no se aplican al instalador gráfico actual.

Descarga `Instalar-Taller-UFV.exe` desde la versión publicada del repositorio.
Es un ejecutable del taller que muestra una consola con el progreso. Lleva el
arranque Python empaquetado; obtiene los demás programas de sus distribuidores.
Obsidian también tiene su propio instalador `.exe`, que este arranque descarga y
ejecuta para el usuario actual.

## Qué sucede al ejecutarlo

1. Descarga el ZIP de la versión fijada, verifica SHA256 y lo extrae en
   `%LOCALAPPDATA%\Programs\TallerUFV\0.6.0\taller-agente-local-ufv`.
2. Ejecuta `preparar.ps1`, el mismo arranque que contiene el repositorio.
3. Pregunta si quieres **OpenCode Desktop** o **solo terminal**. Prepara Python,
   instala Obsidian 1.15.1 en el usuario y prepara Ollama, la CLI de OpenCode,
   Qwen3 4B Instruct y el perfil de hardware. Reutiliza Obsidian si ya existe.
4. Comprueba inferencia, herramientas y una lectura real de los apuntes desde OpenCode.
5. Registra la bóveda del taller y abre Obsidian en `Inicio.md`, junto al tutor.
   No requiere elegir carpeta. Si Obsidian ya está abierto al registrar una bóveda
   nueva, se cierra normalmente y vuelve a abrirse. Se conservan las otras bóvedas
   y se guarda el registro original como `obsidian.json.ufv-backup`.

Si eliges Desktop, instala OpenCode Desktop 2.4.1 mediante el instalador oficial
para tu usuario, verificando SHA256, y abre el proyecto del taller con el tutor y
modelo local ya seleccionados. Si eliges terminal, no descarga ni abre Desktop.
La elección se recuerda en `.local/interfaz.json`. Una versión Desktop 2 en su
ruta habitual se reutiliza. La antigua app 1.x usa otra ruta y otro formato de
configuración; el taller prepara Desktop 2 junto a ella.

El tutor conoce las rutas de apuntes, memoria, ejemplos y documentación. El arranque
conecta y verifica las herramientas de búsqueda y OEE por MCP, sin configuración manual.
El proyecto abierto es la raíz del taller: puedes ver `boveda/`, `docs/`, `solucion/`
y `plantilla/` desde la app. El EXE deja un acceso **Taller UFV 0.6.0** en el menú
Inicio y una copia del lanzador junto al taller instalado. Ese acceso inicia Ollama
si hace falta y abre Obsidian y la interfaz elegida; puedes borrar el EXE descargado.

Desde la versión 0.6 incluye las herramientas de gestión de la carrera: cursos,
asignaturas, temas, apuntes, tareas, exámenes, importación de PDF y agenda local.
El tutor conoce las herramientas y el panel `Carrera.md` de Obsidian.
Consulta [CARRERA.md](CARRERA.md) para probar una sesión completa.

Puedes cambiarlo al ejecutar de nuevo el mismo EXE:

```powershell
.\Instalar-Taller-UFV.exe --ui elegir
.\Instalar-Taller-UFV.exe --ui si
.\Instalar-Taller-UFV.exe --ui no
```

`--ui no` no desinstala una aplicación existente. En ejecuciones sin terminal
interactiva se usa la elección guardada; si no hay ninguna, se usa solo terminal.

La aplicación Obsidian de Windows se instala normalmente en
`%LOCALAPPDATA%\Programs\Obsidian\Obsidian.exe`. La configuración del taller y las
notas permanecen en su carpeta. No se instalan plugins ni se activa sincronización.
No se requieren cuentas para las notas locales.

La descarga inicial requiere internet y varios GB libres. El EXE no incluye el
modelo ni todos los programas dentro del propio archivo. Si se repite con la misma
versión y destino, conserva apuntes, memoria y configuración. Rechaza un destino con
otro paquete en lugar de sobrescribirlo. El EXE no lleva firma de editor propia.
Una vez instalado, reutiliza la carpeta sin descargar el ZIP de nuevo.

## Probar en otra carpeta

Para preparar todo sin dejar un chat interactivo abierto:

```powershell
.\Instalar-Taller-UFV.exe --destino C:\Pruebas\TallerUFV --accion preparar
```

Después abre las notas o inicia la aplicación completa:

```powershell
.\Instalar-Taller-UFV.exe --destino C:\Pruebas\TallerUFV --accion notas
.\Instalar-Taller-UFV.exe --destino C:\Pruebas\TallerUFV
```

La acción `doctor` muestra el estado del entorno. El registro de cada programa
queda dentro de `.local/` en el taller instalado. Conserva el error visible en consola
si falla una descarga o un controlador.

## Construir el EXE desde el código

En Windows, genera primero el ZIP y después empaqueta el arranque:

```powershell
.tools\uv\uv.exe run --python 3.11 python herramientas/empaquetar.py
.tools\uv\uv.exe run --python 3.11 --with pyinstaller==6.22.3 python herramientas/crear_instalador.py
```

El resultado es `dist/Instalar-Taller-UFV.exe`. Incorpora la URL y hash de **ese ZIP**;
publica ambos archivos en la misma versión de GitHub. Si cambia el ZIP, reconstruye
también el EXE. El programa no ejecuta un ZIP cuyo hash sea distinto.
