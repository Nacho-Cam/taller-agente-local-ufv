# Tu agente local, instalado en tu usuario

Descarga el instalador de tu sistema en [la última versión](https://github.com/Nacho-Cam/taller-agente-local-ufv/releases/latest). No necesitas tener Python, Git ni Ollama instalados.

| Equipo | Archivo | Cómo abrirlo |
| --- | --- | --- |
| Windows x64 | `Instalar-Taller-UFV.exe` | Doble clic |
| Mac con M1, M2, M3 o posteriores | `Instalar-Taller-UFV-macOS-arm64.zip` | Extraer y abrir la aplicación |
| Mac Intel | `Instalar-Taller-UFV-macOS-x86_64.zip` | Extraer y abrir la aplicación |
| Linux x64 con escritorio | `Instalar-Taller-UFV-Linux-x86_64.tar.gz` | Extraer y ejecutar `./Instalar-Taller-UFV` |

Los paquetes no están firmados con un certificado comercial ni notarizados por Apple. En macOS puede ser necesario autorizar su apertura desde Ajustes del Sistema > Privacidad y seguridad. La cobertura exacta de pruebas está en [Pruebas multiplataforma](PRUEBAS_MULTIPLATAFORMA.md).

## Elegir componentes

El instalador muestra una ventana con cuatro opciones:

- **OpenCode Desktop:** aplicación de chat; al activarla se activa también su CLI.
- **Obsidian:** editor de tu bóveda, ya conectado a tus apuntes.
- **OpenCode CLI:** chat desde terminal. Puedes desactivar tanto Desktop como CLI para usar el agente Python del taller.
- **Ajustar al rendimiento de mi equipo:** prueba el modelo y ajusta cuántas tareas pueden ejecutarse a la vez. Conviene dejarlo activado en la primera instalación.

Python, Ollama, el modelo LFM3 y las herramientas académicas forman la base obligatoria. El instalador muestra las descargas y comprobaciones en el registro; la primera ejecución necesita Internet y al menos 7 GB libres. No instala controladores gráficos.

Pulsa **Instalar selección** y, cuando termine, **Abrir mi agente**. Los componentes desmarcados no se instalan; la elección se recuerda. Si desmarcas un componente ya instalado, deja de usarse pero no se desinstala automáticamente.

Desde 0.7.1 hay una opción adicional **Preparar conexión con Gemini CLI**, disponible tras instalar. Comparte la bóveda y las herramientas académicas con esa aplicación. Necesita una cuenta admitida y Gemini CLI instalado; el acceso educativo a Gemini web no garantiza acceso a la CLI. [Pasos, requisitos y límites de Gemini](GEMINI.md).

## Dónde queda la aplicación

### Traer una carpeta que ya tienes

En **Traer tus apuntes**, pulsa **Elegir carpeta…** y selecciona tu carpeta de universidad o una bóveda existente. En la primera instalación se importa al pulsar **Instalar selección**. Si ya tienes el taller instalado, pulsa **Importar carpeta a mi bóveda**.

Se hace una copia en `boveda/apuntes/Importados`, manteniendo subcarpetas y archivos originales. La carpeta de origen no se modifica. Los ajustes y plugins de otra bóveda no se importan. Markdown y texto extraído de PDF quedan consultables sin cambiar el contenido de las notas originales; otros formatos se conservan como adjuntos. No se aplica OCR a escaneados. Los enlaces relativos entre archivos copiados se conservan; los enlaces absolutos o configurados por plugins pueden necesitar ajustes.

Puedes importar más carpetas después. Cada importación crea una copia independiente; no sincroniza cambios posteriores ni sobrescribe una importación anterior. Necesitas espacio libre para esa copia y el texto extraído. La búsqueda recorre como máximo 10000 notas y 256 MB de texto por consulta, con hasta 1,25 MB por nota.

Puedes cambiar la carpeta antes de instalar. Por defecto:

| Sistema | Instalación y documentos | Acceso habitual |
| --- | --- | --- |
| Windows | `%LOCALAPPDATA%\Programs\TallerUFV` | Inicio → Taller UFV |
| macOS | `~/Library/Application Support/TallerUFV` | `~/Applications/Taller UFV.app` |
| Linux | `$XDG_DATA_HOME/taller-ufv`, o `~/.local/share/taller-ufv` | Menú de aplicaciones → Taller UFV |

Dentro está `taller-agente-local-ufv/boveda`: tus asignaturas, tareas, exámenes, adjuntos y memoria. **Abrir mis archivos** te lleva allí. Esa carpeta se puede copiar como copia de seguridad y leer con cualquier editor Markdown, incluso sin el modelo.

El acceso conserva su propio lanzador: después de instalar puedes borrar el archivo que descargaste. Al abrirlo arranca el servidor local y la interfaz elegida. También permite cambiar componentes y aplicar una actualización. Los arranques normales reutilizan el entorno; no repiten la calibración.

## Actualizar y recuperar

Abre el instalador de una versión nueva y selecciona la **misma carpeta**. Desde la versión 0.7 el instalador actualiza el código y conserva íntegra la bóveda, los modelos, el entorno y los ajustes. Comprueba los archivos antes de actualizarlos y revierte los cambios si falla una escritura. Si has editado código del programa, pide conservar esos cambios antes de continuar.

Las instalaciones 0.6 y anteriores usaban carpetas por versión. Conserva la anterior, instala la nueva y copia tus documentos personales de su `boveda` a la nueva bóveda; no borres el original hasta comprobar tus asignaturas y adjuntos. Esas versiones no tienen el manifiesto necesario para actualizarlas automáticamente con seguridad.

Si falla una descarga, el registro muestra el motivo y puedes **Reintentar instalación**. Las descargas completadas y verificadas se reutilizan. El registro final queda en `.local/instalacion-ui.log`. Si el error indica que falta o se ha modificado código, conserva la carpeta anterior y elige otra para reinstalar.

## Seguir usándolo después de clase

Empieza en `Carrera.md`. Pide una acción por mensaje: crear un curso, crear una asignatura, añadir un material o consultar la agenda. Los PDFs con texto se importan como adjuntos y notas consultables. El modelo pequeño puede equivocarse: revisa los cambios en tu bóveda, especialmente fechas y asignaturas. [Ejemplos y herramientas académicas](CARRERA.md).

Canvas todavía no está conectado. La integración opcional con Claude Code usa el mismo MCP local y está descrita en [MCP y Claude](MCP_Y_CLAUDE.md).
