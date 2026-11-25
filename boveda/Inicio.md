# Mi asistente de Industria Conectada

El arranque abre esta bóveda en Obsidian y el tutor en OpenCode.
El tutor ya tiene seleccionado el modelo local y conoce las rutas de tus notas.

## Empieza aquí

- «Consulta los apuntes de MQTT y dime qué topic usa la maqueta; cita la fuente».
- «Busca los datos del caso OEE y calcula sus tres factores y el OEE con la herramienta».
- «Recuerda que quiero practicar sensores de 4–20 mA». Revisa y acepta la edición propuesta.
- En otra sesión: «¿Qué quería practicar?».

## Tus materiales

- [[apuntes/OEE]]: caso práctico de una línea de producción ficticia.
- [[apuntes/Sensores]]: ejemplo de sensor de presión con salida de 4–20 mA.
- [[apuntes/MQTT]]: decisiones de comunicación para una práctica ficticia.
- `apuntes/`: añade y edita aquí tus apuntes Markdown para que el tutor los consulte.
- `memoria/`: notas que tú autorizas guardar y que el tutor puede recuperar en otra sesión.

Obsidian y el tutor usan estos mismos archivos; no necesitas copiar las notas entre aplicaciones.
Puedes guardar PDFs en Obsidian, pero el buscador del taller consulta Markdown.

Estos documentos son ejemplos didácticos creados para el taller, no apuntes oficiales
ni especificaciones para operar una instalación industrial real.

Puedes editar o borrar las notas. El agente vuelve a leer los apuntes al buscar.
El agente Python carga las cuatro últimas notas al iniciar; usa `/nuevo` para recargarlas.
OpenCode puede consultar `memoria/` durante la conversación.
