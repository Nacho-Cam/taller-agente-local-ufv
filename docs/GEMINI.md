# Gemini y la cuenta de la universidad

Gemini es opcional. La instalación local funciona con Ollama y Qwen3 4B Instruct sin cuenta de Google ni conexión permanente a Internet.

## Qué se conecta

La opción **Preparar conexión con Gemini CLI** del gestor crea `.gemini/settings.json` y `GEMINI.md` dentro de la carpeta instalada. Gemini CLI podrá buscar apuntes, organizar cursos y asignaturas, importar archivos locales indicados por el alumno y consultar la agenda. Usa la misma bóveda que Obsidian.

Por defecto se habilitan las herramientas académicas y de consulta, sin delegar al modelo de Ollama. La variante de consola permite añadir esa delegación mediante `--modelo-local`. No cambia el modelo ni las credenciales de Google y conserva las otras configuraciones del proyecto. Si encuentra un conector distinto con el mismo nombre o instrucciones personalizadas, se detiene sin sobrescribirlos.

## Qué permite una cuenta universitaria

**Tener Gemini en la web no confirma que Gemini CLI funcione con la cuenta de la universidad.** Google documenta que las cuentas educativas o de Workspace necesitan configurar un proyecto de Google Cloud para usar la CLI, con los permisos y servicios correspondientes. Hay que comprobar qué permite la UFV; el instalador no concede licencias ni permisos institucionales.

Referencias oficiales: [autenticación de Gemini CLI](https://geminicli.com/docs/get-started/authentication/) y [Gemini Apps con cuenta educativa](https://support.google.com/gemini/answer/14620100).

## Pasos para el alumno

1. Instala el taller normalmente y termina su preparación.
2. En el gestor, desplázate hasta **Preparar conexión con Gemini CLI** y pulsa el botón.
3. Si aún no tienes Gemini CLI, sigue su [instalación oficial](https://geminicli.com/docs/get-started/installation/). Requiere Node.js 20 o posterior; el instalador del taller no instala esta aplicación adicional. Con Node disponible, el comando oficial es `npm install -g @google/gemini-cli`.
4. Abre una terminal en la carpeta `taller-agente-local-ufv` de la instalación y ejecuta `gemini`.
5. Selecciona **Sign in with Google** e inicia sesión tú mismo en el navegador. Si la cuenta educativa pide un proyecto Cloud o un permiso que no tienes, utiliza el agente local del taller mientras la universidad confirma el acceso.
6. Comprueba `/mcp`: debe aparecer `ufv-local`. Prueba «Busca el topic MQTT de la maqueta en mis apuntes y cita la fuente».

La conexión prepara archivos y herramientas; no inicia sesión por ti. La prueba automática valida configuración y protocolo MCP sin llamar a la API de Google. No se ha validado una cuenta de alumno de la UFV.

Para conectar otro proyecto desde consola, usa el `uv` portable del taller:

```sh
uv run --python 3.11 --extra mcp python herramientas/conectar_gemini.py --destino RUTA_DEL_PROYECTO
```

Ejecuta ese comando desde la carpeta del taller. En Windows el ejecutable portable es `.tools\uv\uv.exe`; en macOS/Linux es `.tools/uv/uv`.

## Canvas y los documentos

**Canvas LMS sigue sin conectar ni sincronizar.** Iniciar sesión en Gemini no da acceso automático al campus de la universidad. Hoy puedes descargar un PDF desde Canvas y pedir que se importe en una asignatura indicando su ruta local. El importador conserva el original y extrae el texto de los PDFs que lo contienen; los escaneados necesitan OCR adicional.

Gemini usa un servicio remoto. Los fragmentos que le entreguen las herramientas pueden procesarse en Google bajo las condiciones de la cuenta utilizada. Para mantener toda la conversación local, usa el agente con Ollama.
