# Para preparar el portátil antes del taller

El jueves construiremos un asistente de estudio local que consulta apuntes y
puede guardar notas entre sesiones. Traed **portátil y cargador**.

Antes de venir:

1. En Windows descargad **Instalar-Taller-UFV.exe** desde [la versión actual del taller](https://github.com/Nacho-Cam/taller-agente-local-ufv/releases/latest)
   y ejecutadlo. Como alternativa, descargad el ZIP, extraedlo y abrid `iniciar.cmd`.
2. En macOS/Linux descargad el ZIP, extraedlo y ejecutad `bash iniciar.sh` en esa carpeta.
3. Dejad que prepare Python, Obsidian, Ollama, el modelo LFM3 1.7B y OpenCode. Puede descargar
   varios GB; hacedlo en casa antes de clase, con al menos 7 GB libres.
   Elegid si queréis la aplicación de escritorio de OpenCode o usar solo terminal.
4. Obsidian se abre directamente en la nota `Inicio` de la bóveda del taller.
   No hace falta elegir carpeta ni configurar plugins.
5. Cuando se abra el tutor, probad «Consulta los apuntes de MQTT y dime qué topic
   utiliza la maqueta; cita la fuente».

La preparación detecta el equipo, ajusta contexto y concurrencia, y comprueba
que el modelo puede pedir herramientas. Si aparece un error, guardad el mensaje
y avisad para preparar una alternativa o trabajar por parejas.

Como orientación: portátil con **16 GB de RAM**. Una NVIDIA con memoria suficiente
o un Mac Apple Silicon pueden acelerar el modelo. También hay un perfil CPU.
Los controladores de la GPU deben estar instalados; el programa no los sustituye.

No hace falta instalar Git, Node, T3 ni disponer de cuentas de pago o claves API.
**Obsidian se instala** para abrir y editar la carpeta `boveda/` como notas.
Usaremos apuntes ficticios incluidos; no hace falta conectar Canvas.

Si ya tenéis Ollama, el taller usa un servidor local independiente. Para ayuda y
opciones manuales, consultad [ENTORNO.md](ENTORNO.md).
