# Tu asistente de la carrera

El tutor de OpenCode y el agente Python tienen herramientas de gestión académica.
El arranque prepara las dependencias y conecta las herramientas automáticamente.
Obsidian muestra las mismas carpetas y un panel `Carrera.md`, actualizado tras cada operación.
No trae un plan de estudios inventado: añade tus cursos y asignaturas reales desde el chat.

## Una sesión de principio a fin

1. «Crea el curso 2026-2027 tercero y la asignatura Automatización».
2. «Añade el tema Sensores a Automatización de ese curso. Incluye salidas de 4–20 mA y calibración».
3. «Añade el apunte Sensor P-101 al tema Sensores. El rango es de 0 a 10 bar y la salida de 4 a 20 mA».
4. «Añade la tarea Práctica P-101 a esa asignatura, tema Sensores, para el 2026-11-30. Hay que calcular qué presión representan 12 mA».
5. «Añade el examen Parcial para el 2026-12-10; entran Sensores y MQTT».
6. «¿Qué tengo pendiente en ese curso?».
7. «Marca la tarea Práctica P-101 como completada». El tutor obtiene su ID con `listar_carrera`.
8. «Prepara cinco preguntas para el parcial usando los materiales de esa asignatura y cita las fuentes».

Los nombres pueden ser tuyos: «Segundo», «2026-2027 segundo» o «Máster 2026-2027».
Una asignatura con el mismo nombre en dos cursos se gestiona por separado.
El tutor pide el curso si es necesario para identificar la asignatura.

## Herramientas concretas

| Herramienta | Uso |
|---|---|
| `listar_carrera` | Cursos y asignaturas; con ambos filtros, materiales e IDs. |
| `crear_curso` | Crea un curso sin duplicarlo al repetir la petición. |
| `crear_asignatura` | Crea la asignatura y sus carpetas dentro del curso. |
| `quitar_asignatura` | Archiva la carpeta completa en la papelera de la bóveda. |
| `restaurar_asignatura` | Recupera la carpeta sin sobrescribir otra asignatura activa. |
| `anadir_material` | Añade un tema, apunte, tarea o examen con tema, contenido y fecha. |
| `importar_material` | Importa un archivo local como material, conserva el original y extrae su texto cuando es posible. |
| `actualizar_tarea` | Cambia el estado de una tarea o examen y, si se indica, su fecha. |
| `quitar_material` | Retira su nota a la papelera y conserva el adjunto original. |
| `consultar_agenda` | Tareas y exámenes pendientes por fecha, con los vencidos señalados. |
| `buscar_apuntes` | Busca contenidos, incluidos PDFs importados; permite filtrar por curso y asignatura. |

Estados: `pendiente`, `en_curso` y `completado`. Fechas: `AAAA-MM-DD`.
Completar una tarea actualiza la agenda local; no entrega nada en Canvas LMS.
Las operaciones de gestión se ejecutan cuando el alumno las pide. Los resultados
de las herramientas confirman lo que se ha creado, actualizado o archivado.

## Importar materiales

Pide: «Importa el PDF `C:\Users\Alumno\Downloads\tema-2.pdf` como apunte de
Automatización, curso 2026-2027 tercero, tema Sensores, título Tema 2».
Puedes indicar la ruta arrastrando o pegando el archivo en el chat si tu interfaz lo permite.

La herramienta copia el archivo a `adjuntos/`, mantiene intacto el original y crea
una nota con su texto y referencias a las páginas. Esa nota ya entra en la búsqueda.
Admite adjuntos de hasta 32 MB. Extrae texto de PDF, Markdown, TXT y CSV. Imágenes,
DOCX y PPTX se conservan como adjuntos; no se extrae su contenido.
Los PDFs cifrados necesitan una copia sin contraseña. Los escaneados sin texto necesitan
OCR externo. Para mantener el entorno ligero, se extraen hasta 100 páginas y unos
200000 caracteres de PDF. El resultado indica si hubo limitación.

## Carpetas compartidas con Obsidian

```text
boveda/
  Carrera.md
  cursos/
    curso-2026-2027-tercero/
      Curso.md
      asignaturas/
        asignatura-automatizacion/
          Asignatura.md
          temas/
          apuntes/
          tareas/
          examenes/
          adjuntos/
  papelera/
    asignaturas/
    materiales/
```

Las notas contienen propiedades de Obsidian con curso, asignatura, tema, fecha y estado.
Puedes editar el texto de los materiales en Obsidian y el tutor lo leerá al buscar.
El panel se regenera con las operaciones del tutor o al arrancar el entorno.
Cursos, materiales, panel y papelera se excluyen de Git y del ZIP público.

## Otros clientes MCP

El servidor estándar conserva sus tres herramientas de consulta. Para habilitar
también gestión académica en otro cliente, añade `--gestion-academica` al comando
de `integraciones/servidor_mcp.py`, junto con `--boveda RUTA`.
OpenCode ya recibe esa configuración del instalador. La delegación de consulta y
el ejemplo de equipo siguen trabajando en modo lectura.
