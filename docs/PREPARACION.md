# Para preparar el portátil antes del taller

El jueves construiremos un asistente de estudio local que consulta apuntes y
puede guardar notas entre sesiones. Traed **portátil y cargador**.

Antes de venir:

1. Descargad el ZIP desde [la versión actual del taller](https://github.com/Nacho-Cam/taller-agente-local-ufv/releases/latest).
2. Extraed la carpeta completa.
3. En Windows, abrid **iniciar.cmd**. En macOS/Linux, abrid una terminal en esa
   carpeta y ejecutad `bash iniciar.sh`.
4. Dejad que prepare Python, Ollama, el modelo LFM3 1.7B y OpenCode. Puede descargar
   varios GB; hacedlo en casa antes de clase, con al menos 7 GB libres.
5. Cuando se abra el tutor, probad «Consulta los apuntes de MQTT y dime qué topic
   utiliza la maqueta; cita la fuente».

La preparación detecta el equipo, ajusta contexto y concurrencia, y comprueba
que el modelo puede pedir herramientas. Si aparece un error, guardad el mensaje
y avisad para preparar una alternativa o trabajar por parejas.

Como orientación: portátil con **16 GB de RAM**. Una NVIDIA con memoria suficiente
o un Mac Apple Silicon pueden acelerar el modelo. También hay un perfil CPU.
Los controladores de la GPU deben estar instalados; el programa no los sustituye.

No hace falta instalar Git, Node, T3 ni disponer de cuentas de pago o claves API.
**Obsidian es opcional** para abrir y editar la carpeta `boveda/` como notas.
Usaremos apuntes ficticios incluidos; no hace falta conectar Canvas.

Si ya tenéis Ollama, el taller usa un servidor local independiente. Para ayuda y
opciones manuales, consultad [ENTORNO.md](ENTORNO.md).
