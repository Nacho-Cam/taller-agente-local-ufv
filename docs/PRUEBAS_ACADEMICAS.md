# Pruebas del recorrido de un alumno

Comprobación del 26 de noviembre de 2026 con OpenCode 2.4.1, Ollama 0.40.18,
Qwen3 4B Instruct Q4, contexto 8192 y una tarea simultánea. Equipo de prueba:
Windows, RTX 2060 de 6 GB y 32 GB de RAM.

## Resultado real con el modelo

**14 de 14 casos correctos**, con tiempos de 6 a 16,2 segundos por petición:

| Recorrido | Comprobación |
|---|---|
| Importar una carpeta existente | El importador del instalador vincula los apuntes; el tutor recupera un dato de una asignatura sin organización manual. |
| Documento general | Encuentra un dato en una carpeta que no tiene curso ni asignatura. |
| Asignaturas | Devuelve las asignaturas registradas del curso pedido. |
| Materiales | Distingue tema, apunte y tarea, sin duplicar sus títulos. |
| Contenido de apuntes | Recupera presión y válvula de una nota y presenta su fuente. |
| Asignatura inexistente | Informa de que no existe, sin crearla. |
| Crear asignatura | Curso y asignatura aparecen realmente en disco. |
| Añadir tarea | Conserva título, contenido, tema y fecha. |
| Añadir examen | Conserva tipo examen, tema y fecha. |
| Agenda | Muestra la tarea pendiente y su fecha. |
| Completar tarea | El estado guardado cambia a completado. |
| Importar PDF | Conserva el original e incorpora su texto al material. |
| Archivar asignatura | La retira del curso conservándola en papelera. |
| Restaurar asignatura | Vuelve a aparecer en el curso. |

Se usa una bóveda ficticia separada, archivos reales y herramientas MCP reales.
Se revisan tanto las llamadas y respuestas como el estado de los archivos después
de las acciones. Los informes completos se guardan en `.local/`, fuera de Git.

LFM3 1.7B se probó en el mismo recorrido. Mejoró al precisar los esquemas de las
herramientas, pero siguió fallando al crear un examen e importar un PDF. Por eso
Qwen es el modelo principal de esta versión; LFM3 sigue disponible para comparar.

## Repetir la prueba

Desde una instalación preparada, en Windows:

```powershell
.tools\uv\uv.exe run --frozen --extra mcp python herramientas/evaluar_carrera.py
```

En macOS o Linux cambia el ejecutable a `.tools/uv/uv`. Usa `--modelo` para
comparar un modelo ya descargado. No se cambian el modelo ni los apuntes de la
instalación: cada evaluación crea su propio espacio de trabajo.

El evaluador espera a que el MCP esté conectado antes de preguntar, como en la
aplicación de escritorio. Arrancar una instancia independiente de OpenCode por
cada pregunta producía errores al intentar usar herramientas aún no cargadas.

## Pruebas del código y límites

La suite local completa ejecutó **118 pruebas, con 3 omitidas según el entorno**.
Cubre importación automática, búsqueda con filtros, paginación de materiales,
referencias a adjuntos, conservación de ediciones y rechazo de enlaces externos.

En la RTX 2060 se emplea un perfil compatible con CUDA 12, sin fusión, grafos ni
caché de contexto. Las primeras pruebas con el perfil anterior se bloquearon.
Este resultado no constituye una prueba de inferencia en todos los modelos de
GPU ni en macOS/Linux; los instaladores tienen comprobaciones separadas en CI.
Los PDFs escaneados sin texto necesitan OCR externo y Canvas no está conectado.
