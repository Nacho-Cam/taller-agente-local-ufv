# Pruebas e instaladores por sistema

El flujo [Instaladores y pruebas multiplataforma](../.github/workflows/instaladores.yml) se ejecuta con cada cambio en `main`, en solicitudes de cambio y manualmente desde GitHub Actions. Los trabajos tienen permisos de lectura; no publican versiones ni modifican el ordenador de ningún alumno.

| Sistema probado | Runner nativo | Instalador esperado |
| --- | --- | --- |
| Windows x64 | `windows-2022` | `.exe` |
| macOS Apple Silicon | `macos-15`, ARM64 | `.app` dentro de un ZIP |
| macOS Intel | `macos-15-intel`, x64 | `.app` dentro de un ZIP |
| Linux x64 | `ubuntu-22.04` | ejecutable dentro de `.tar.gz` |

Las etiquetas de macOS se eligen según la [referencia oficial de runners](https://docs.github.com/en/actions/reference/runners/github-hosted-runners). No se incluye Windows ARM64 ni Linux ARM64 en esta matriz.

## Qué verifica automáticamente

**Validación de 0.7.0:** [ejecución completa terminada correctamente](https://github.com/Nacho-Cam/taller-agente-local-ufv/actions/runs/45735664517), sobre el código `587a027`: Windows x64, macOS Apple Silicon, macOS Intel y Linux x64. Además del instalador y las herramientas, se descargaron los componentes reales y cada sistema obtuvo una respuesta del modelo local.

En Windows también se descargó el EXE publicado y se instaló en la carpeta definitiva de un usuario real con una RTX 2060. Se verificaron aceleración GPU, dos peticiones simultáneas, lectura desde OpenCode, MCP, apertura de Obsidian, actualización conservando una nota y reapertura desde Inicio sin depender del EXE descargado. La nota temporal se retiró después de comprobar su integridad.

1. Instala las dependencias del archivo de bloqueo, usando Python 3.11 del sistema de pruebas y su biblioteca Tk.
2. Ejecuta la batería `unittest`: gestión de asignaturas y materiales, aislamiento de rutas, importación PDF, agenda, configuración, protocolo MCP y perfiles de hardware simulados.
3. Abre la interfaz gráfica y ejecuta `--prueba-ui`, sin descargar modelos ni instalar aplicaciones. En Linux usa una pantalla virtual Xvfb.
4. Construye un instalador con PyInstaller en cada sistema y repite la prueba de interfaz desde ese ejecutable.
5. Conserva los instaladores como artefactos durante 14 días. Un fallo en una plataforma no cancela las demás; cada resultado se puede revisar por separado.

La ejecución manual ofrece **`instalacion_completa`**. Si se activa, también ejecuta los lanzadores reales, descarga Ollama, LFM3, OpenCode CLI/Desktop y Obsidian, verifica MCP y pide una respuesta al modelo. Omite la calibración larga y no abre el chat de las aplicaciones de terceros. Las ejecuciones habituales de cada cambio omiten esta descarga completa.

El ZIP del repositorio se crea **una sola vez** y se comparte entre los cuatro trabajos. Cada instalador incorpora el SHA256 de ese mismo archivo. Al preparar una versión hay que publicar ese ZIP canónico junto con sus instaladores: regenerarlo después puede cambiar su hash aunque el contenido sea equivalente.

## Qué requiere una comprobación real adicional

Una ejecución verde habitual confirma las pruebas y el arranque de la interfaz dentro de esos runners. La opción manual anterior añade descargas e inferencia reales. No demuestra por sí sola:

- El comportamiento completo de las ventanas de Obsidian y OpenCode en cada portátil; se instalaron sus componentes en los runners, pero sus chats no se automatizan allí.
- Rendimiento, memoria disponible o aceleración de una GPU concreta. Los runners no representan las GPU de los alumnos.
- El comportamiento de antivirus, Gatekeeper, permisos corporativos o restricciones de la red universitaria.
- La calidad de cada respuesta del modelo o la corrección de una tarea con varias acciones consecutivas.

No se debe marcar una plataforma como comprobada hasta consultar una ejecución terminada del flujo correspondiente. El instalador de macOS no está firmado ni notarizado mientras no se configure una identidad de Apple; la compilación correcta no elimina las comprobaciones de Gatekeeper.

## Comprobación antes del taller

En un usuario o máquina de prueba: descargar el instalador publicado, elegir componentes y carpeta, terminar la preparación, abrir el tutor desde su acceso habitual y crear una asignatura con una tarea. Cerrar y abrir de nuevo, comprobar la agenda, los documentos y las preferencias; repetir el instalador sobre la misma ubicación para comprobar que conserva los datos. Revisar también la elección sin interfaz de chat y sin Obsidian.

Para probar sólo la ventana desde el repositorio:

```sh
uv run --extra mcp python herramientas/instalador_ui.py --prueba-ui
```

Las pruebas automáticas usan carpetas temporales para los datos académicos. Una captura de pantalla y una inspección visual siguen siendo necesarias para revisar recortes, escalado de texto y legibilidad de la interfaz.
