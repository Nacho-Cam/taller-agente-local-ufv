# Alcance y decisiones

## Memoria: Markdown como primera opción

Para una hora, el soporte de memoria son archivos locales `.md`. Obsidian puede
abrir la misma carpeta y mostrar las notas que escribe el programa. La práctica
no depende de instalar Obsidian ni de sus plugins.

Distinguimos tres cosas:

| Elemento | Persistencia y uso |
|---|---|
| Apuntes | Archivos `.md` que se vuelven a leer al buscar. No se entrenan los pesos. |
| Memoria | Notas autorizadas que persisten en disco. Se cargan las cuatro últimas al iniciar o usar `/nuevo`; las demás se buscan. |
| Historial | Mensajes en RAM. Se reinicia al cerrar o superar el límite práctico del programa. |

La búsqueda es léxica: normaliza acentos y busca coincidencias en bloques de líneas.
No hay embeddings, índice vectorial ni un grafo de conocimiento.
Se leen hasta 100 `.md` por carpeta, cada uno de hasta 100 KB, en `apuntes/` y
`memoria/`, sin subcarpetas. Es un límite del ejemplo, pensado para una bóveda pequeña.
Devuelve como máximo cuatro fragmentos de 1400 caracteres.
Los enlaces `[[...]]` se ven en Obsidian; el agente no los recorre como un grafo.

GBrain puede ser una ampliación si después se quiere una capa de memoria compartida,
procedencia y búsqueda más elaborada. Añade instalación y conceptos que no necesitamos
para observar el ciclo básico. No se ha integrado ni validado en este taller.

Referencias consultadas:

- [Cómo almacena datos Obsidian](https://obsidian.md/help/data-storage).
- [GBrain: documentación del proyecto](https://github.com/garrytan/gbrain).

## Ollama y modelo

**Actualización 0.2:** el arranque automático usa LFM3 1.7B Q4, ajusta contexto y
concurrencia, y añade OpenCode 2 Mini. Consulta [ENTORNO.md](ENTORNO.md) y el registro
de validación. Lo que sigue describe Qwen como recorrido manual de respaldo.

Se propone `qwen3:4b-instruct`, cuantizado, cuya descarga publicada ronda 2,5 GB.
`qwen3:1.7b` es una alternativa más pequeña con posibles diferencias de calidad.
Estos tamaños no indican toda la RAM necesaria. El contexto se limita a 8192 tokens
y cada respuesta a 700 tokens; el historial se reinicia al superar un umbral de texto.
El rendimiento depende del equipo, la aceleración disponible y otras aplicaciones.

El agente usa `/api/chat`, esquemas de herramientas y `think: false`. El programa
ejecuta las funciones y añade sus resultados como mensajes de herramienta.
Hay un máximo de cuatro rondas con herramientas y ocho llamadas a herramientas por
turno. Si agota las rondas, se permite una última respuesta sin herramientas con
los resultados recuperados. Si tampoco responde, el turno termina con un error;
las notas ya confirmadas permanecen.

- [Modelo propuesto](https://ollama.com/library/qwen3:4b-instruct).
- [Ciclo de herramientas en Ollama](https://github.com/ollama/ollama/blob/main/docs/capabilities/tool-calling.mdx).
- [Control del razonamiento](https://github.com/ollama/ollama/blob/main/docs/capabilities/thinking.mdx).

## PDF y documentos de asignaturas

Esta versión lee Markdown. Que un PDF esté en una bóveda de Obsidian no lo hace
consultable por este programa. Para el taller, convierte antes un fragmento breve
a texto Markdown y comprueba su contenido, fórmulas y tablas.
Un PDF escaneado requeriría OCR; no forma parte de esta hora.

## Canvas LMS: ampliación posterior

Para la sesión, descarga manualmente un documento accesible de una asignatura y
prepara una versión Markdown. La práctica no incluye conexión a Canvas.

Una integración posterior podría sincronizar archivos o tareas mediante su API.
Necesitaría verificar el dominio de la UFV, los permisos de alumno y el mecanismo
de autenticación autorizado por la institución. No se ha comprobado ese acceso.
Canvas documenta la generación manual de tokens para pruebas propias, y exige
OAuth para aplicaciones que piden acceso a otros usuarios: no se plantea repartir
un formulario para que toda la clase pegue tokens personales.

- [API de archivos](https://www.sso.canvaslms.com/doc/api/files.html).
- [Autenticación OAuth de Canvas](https://www.sso.canvaslms.com/doc/api/file.oauth.html).

## Herramienta de ingeniería

OEE es un ejemplo didáctico con datos ficticios. La función calcula con unidades
definidas y rechaza datos inconsistentes. El modelo no ejecuta código arbitrario:
solo puede solicitar las tres funciones permitidas por el programa.
No controla maquinaria, modifica Canvas ni navega por la web.
