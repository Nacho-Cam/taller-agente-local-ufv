# Preparación y guion del ponente

Sesión prevista: jueves 26 de noviembre de 2026, 12:30–15:00.
Este documento reserva una hora al taller; la distribución del resto es una propuesta
pendiente de acordar con Álvaro. No se presuponen datos de tu trayectoria.

## Distribución posible de las dos horas y media

| Horario | Contenido |
|---|---|
| 12:30–12:40 | Bienvenida y presentación breve de tu paso por la UFV. |
| 12:40–13:00 | A qué te dedicas y un caso concreto de tu trabajo actual. |
| 13:00–13:15 | Conversación sobre carrera, proyectos y preguntas. |
| 13:15–13:25 | Pausa y preparación de portátiles. |
| 13:25–14:25 | Taller de 60 minutos. |
| 14:25–14:45 | Mostrar trabajos de parejas y resolver dudas. |
| 14:45–15:00 | Preguntas abiertas, siguientes pasos y cierre. |

## Presentación personal: cinco apoyos, unos diez minutos

Completa estos huecos con hechos tuyos antes de preparar diapositivas:

1. **Cuando estaba en vuestro sitio.** Año de promoción y qué te atrajo de la carrera.
2. **Un proyecto de la universidad.** Qué querías hacer, qué construiste tú y qué salió mal.
   Lleva una foto, captura o pieza concreta si la tienes.
3. **Lo que sí me llevé de la carrera.** Una habilidad que hayas usado después,
   acompañada de una situación real.
4. **Mi trabajo ahora.** Para quién resuelves qué problema y cómo es un día normal.
   Evita una lista de tecnologías; enseña una decisión o un resultado.
5. **El puente hacia el taller.** «Vamos a construir una versión pequeña de una idea
   que podéis aplicar a vuestras asignaturas: un programa que usa un modelo,
   consulta información y ejecuta herramientas».

No rellenar empresa, responsabilidades ni logros sin tus datos.

## Antes del jueves

- Enviar `PREPARACION.md` a Álvaro para que los alumnos ejecuten el arranque automático
  antes de clase. Prepara Python, Ollama, LFM3 y OpenCode. Confirmar curso, número de alumnos y horario del taller.
- Ejecutar `--doctor` y los cinco casos del ensayo en TU portátil, con los mismos
  archivos que recibirán los alumnos. Cronometrar la primera respuesta y una en caliente.
- Preguntar por proyector/adaptador, enchufes y wifi. Llevar cargador.
- Llevar el ZIP en el portátil y en un USB. El ZIP no contiene Python, Ollama ni el modelo.
  La práctica offline requiere que estén instalados y el modelo descargado.
- Llevar una captura o grabación propia de un ensayo correcto. No presentarla como directo.
- Si nadie ha podido preparar el equipo, hacer una demostración compartida y dedicar
  la parte práctica a editar apuntes y completar el bucle por parejas.

## Demostración inicial: tres minutos

Abre el agente y una carpeta con los apuntes, lado a lado.

Enseña también el caso de uso académico: crea un curso y una asignatura, añade una
tarea y un examen con fechas, consulta la agenda y muestra `Carrera.md` en Obsidian.
Para que puedan seguirlo sin inventar datos de sus asignaturas, usa los ejemplos de
[CARRERA.md](CARRERA.md). Después pueden incorporar sus materiales reales.

1. «Busca el topic MQTT que usamos en nuestra maqueta y cita la fuente».
2. «Recuerda que quiero repasar OEE con ejemplos de fabricación». Confirma la nota.
3. Reinicia y pregunta qué querías repasar. Enseña el archivo persistente.

Después enseña `solucion/agente.py`: es el bucle que van a completar.
No necesitas explicar todas las utilidades de `nucleo.py` al principio.

## Ensayo mínimo antes de entrar

| Prueba | Evidencia a comprobar |
|---|---|
| MQTT | Llama a buscar y menciona el topic `taller/linea-roble/temperatura` con fuente. |
| Memoria | Propone nota, pide confirmación y la recuerda después de reiniciar. |
| OEE | Busca datos y llama a calcular; el resultado es 67,8571 %. |
| Dato ausente | Pregunta por calibración del sensor; debe reconocer que no está especificada. |

Las pruebas deterministas del código no sustituyen este ensayo: el modelo puede
omitir herramientas, citar mal o dar respuestas distintas con otra versión.

## Puntos de control durante la hora

- Minuto 5: si alguien sigue instalando, emparejarlo con otra persona.
- Minuto 25: toda pareja debe ver una llamada real a `buscar_apuntes`.
- Minuto 35: deben recuperar un dato que hayan añadido ellos.
- Minuto 45: deben poder abrir una nota persistente y explicar por qué no es entrenamiento.
- Minuto 55: OEE es ampliación; si vais tarde, muéstralo tú y prioriza que entiendan la memoria.

Si el modelo se atasca encadenando búsqueda y cálculo, divide la petición.
Si no usa una herramienta, pídesela por su nombre y con argumentos explícitos.
Si agota rondas, usa `/nuevo`; las notas ya confirmadas permanecen en disco.
No conviertas los fallos en diez minutos de depuración ante la clase.

## Respuesta propuesta a Álvaro

Hola, Álvaro:

¡Sí, seguimos adelante! Haré una presentación breve de mi paso por la carrera y
de mi trabajo actual, y me gustaría reservar aproximadamente una hora para una
actividad práctica: construir un pequeño asistente local que consulte apuntes
y guarde notas para futuras sesiones.

Que traigan portátil y cargador. Te paso un arranque que prepara Python, Ollama,
el modelo, OpenCode y Obsidian antes de venir. La bóveda de apuntes se abre
automáticamente en Obsidian.
Llevaré una plantilla y una versión completa en GitHub para que puedan seguir
y continuar después. Podemos trabajar por parejas si algún equipo da problemas.

¿Me confirmas el curso y cuántos alumnos serán? Por mi parte cuento con la franja
de 12:30 a 15:00; ajustamos dentro de ella la charla, la práctica y las preguntas.

¡Un abrazo!
