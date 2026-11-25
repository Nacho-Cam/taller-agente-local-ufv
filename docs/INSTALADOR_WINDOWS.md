# Instalador EXE de Windows

Descarga `Instalar-Taller-UFV.exe` desde la versión publicada del repositorio.
Es un ejecutable del taller que muestra una consola con el progreso. Lleva el
arranque Python empaquetado; obtiene los demás programas de sus distribuidores.
Obsidian también tiene su propio instalador `.exe`, que este arranque descarga y
ejecuta para el usuario actual.

## Qué sucede al ejecutarlo

1. Descarga el ZIP de la versión fijada, verifica SHA256 y lo extrae en
   `%LOCALAPPDATA%\Programs\TallerUFV\0.4.0\taller-agente-local-ufv`.
2. Ejecuta `preparar.ps1`, el mismo arranque que contiene el repositorio.
3. Prepara Python, instala Obsidian 1.15.1 en el usuario y prepara Ollama, OpenCode,
   LFM3 y el perfil de hardware. Reutiliza Obsidian si ya existe.
4. Comprueba inferencia, herramientas y una lectura real de los apuntes desde OpenCode.
5. Abre Obsidian y el tutor. En Obsidian, selecciona **Abrir carpeta como bóveda**
   y elige `boveda` dentro de la ruta que muestra la consola. Solo hace falta la primera vez.

La aplicación Obsidian de Windows se instala normalmente en
`%LOCALAPPDATA%\Programs\Obsidian\Obsidian.exe`. La configuración del taller y las
notas permanecen en su carpeta. No se instalan plugins ni se activa sincronización.
No se requieren cuentas para las notas locales.

La descarga inicial requiere internet y varios GB libres. El EXE no incluye el
modelo ni todos los programas dentro del propio archivo. Si se repite con la misma
versión y destino, conserva apuntes, memoria y configuración. Rechaza un destino con
otro paquete en lugar de sobrescribirlo. El EXE no lleva firma de editor propia.

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
