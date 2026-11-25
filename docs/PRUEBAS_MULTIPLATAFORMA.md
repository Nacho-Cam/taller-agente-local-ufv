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

1. Instala las dependencias del archivo de bloqueo, usando Python 3.11 del sistema de pruebas y su biblioteca Tk.
2. Ejecuta la batería `unittest`: gestión de asignaturas y materiales, aislamiento de rutas, importación PDF, agenda, configuración, protocolo MCP y perfiles de hardware simulados.
3. Abre la interfaz gráfica y ejecuta `--prueba-ui`, sin descargar modelos ni instalar aplicaciones. En Linux usa una pantalla virtual Xvfb.
4. Construye un instalador con PyInstaller en cada sistema y repite la prueba de interfaz desde ese ejecutable.
5. Conserva los instaladores como artefactos durante 14 días. Un fallo en una plataforma no cancela las demás; cada resultado se puede revisar por separado.

El ZIP del repositorio se crea **una sola vez** y se comparte entre los cuatro trabajos. Cada instalador incorpora el SHA256 de ese mismo archivo. Al preparar una versión hay que publicar ese ZIP canónico junto con sus instaladores: regenerarlo después puede cambiar su hash aunque el contenido sea equivalente.

## Qué requiere una comprobación real adicional

Una ejecución verde confirma las pruebas y el arranque de la interfaz dentro de esos runners. No demuestra por sí sola:

- Una instalación completa del modelo, Obsidian y OpenCode en cada portátil.
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
