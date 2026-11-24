# Para preparar el portátil antes del taller

El jueves construiremos un pequeño asistente de estudio que funciona en vuestro
portátil, consulta unos apuntes y puede guardar notas entre sesiones.

Traed **portátil y cargador**. Podremos trabajar por parejas.

Antes de venir:

1. Instalad [Python](https://www.python.org/downloads/) 3.9 o superior, preferiblemente
   3.11+. En Windows, activad la opción de añadir Python al PATH, si aparece.
2. Instalad y abrid [Ollama](https://ollama.com/download).
3. Abrid una terminal y ejecutad:

   ```sh
   ollama pull qwen3:4b-instruct
   ```

   El modelo descarga unos 2,5 GB: hacedlo antes de llegar a clase.
4. Descargad y extraed el [repositorio del taller](https://github.com/Nacho-Cam/taller-agente-local-ufv)
   desde **Code → Download ZIP**. Git es opcional.
5. Abrid una terminal en la carpeta del proyecto. En Windows:

   ```powershell
   py solucion/agente.py --doctor
   py solucion/agente.py --pregunta "Hola, responde con una frase en español."
   ```

   En macOS/Linux sustituid `py` por `python3`. El diagnóstico debería mostrar
   conexión y soporte de herramientas; la segunda orden comprueba una respuesta real.

Como orientación, se recomienda un portátil con 16 GB de RAM o más. Si el vuestro
va lento, avisad para preparar una alternativa o trabajar por parejas.
Ollama y el modelo necesitan espacio adicional a la descarga.

**Opcional:** instalad [Obsidian](https://obsidian.md/) para ver y editar la memoria
como una bóveda de notas. El taller también funciona con un editor de texto.

No hacen falta cuentas de pago, claves API ni acceso de programación a Canvas.
Usaremos apuntes de ejemplo incluidos en el proyecto.
