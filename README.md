# Tu primer agente local · UFV

Taller de una hora para Ingeniería de la Industria Conectada.
Construye un asistente que consulta apuntes, guarda memoria entre sesiones y usa
una función de Python para calcular el OEE de una línea ficticia.

**Ollama + Python + archivos Markdown.** Sin paquetes Python externos, claves API,
Docker ni base de datos. Obsidian es opcional. La práctica no se conecta a Canvas.

## Antes de venir

1. Instala [Python](https://www.python.org/downloads/) 3.9 o superior (recomendado 3.11+).
   En Windows, activa la opción de añadir Python al PATH, si aparece.
2. Instala y abre [Ollama](https://ollama.com/download).
3. Descarga el modelo **antes de clase** desde una terminal:

   ```sh
   ollama pull qwen3:4b-instruct
   ```

La descarga del modelo ronda 2,5 GB; necesita memoria adicional al ejecutarse.
Como orientación para este taller, empieza con 16 GB de RAM o más y espacio libre
para Ollama y el modelo. No es una garantía de velocidad: ejecuta el diagnóstico
y una pregunta en tu portátil. Hay una alternativa de menor tamaño más abajo.
Con las descargas terminadas, el programa usa únicamente Ollama en `127.0.0.1`.

## Descarga y arranque

Usa **Code → Download ZIP** en este repositorio y extrae la carpeta, o clónalo:

```sh
git clone https://github.com/Nacho-Cam/taller-agente-local-ufv.git
cd taller-agente-local-ufv
```

Abre una terminal dentro de la carpeta extraída o clonada. En Windows:

```powershell
py solucion/agente.py --doctor
py solucion/agente.py
```

En macOS y Linux:

```sh
python3 solucion/agente.py --doctor
python3 solucion/agente.py
```

El diagnóstico verifica conexión, modelo y soporte declarado de herramientas;
una pregunta comprueba además la inferencia. Prueba:

> Busca los datos de la Línea Roble en mis apuntes y calcula su OEE usando la herramienta.

Debe mostrar llamadas a `buscar_apuntes` y `calcular_oee`. El OEE de referencia es
**67,8571 %**. La traza muestra qué funciones se ejecutan realmente.

## Dos recorridos

| Carpeta | Para qué sirve |
|---|---|
| `plantilla/` | Completar tres TODO siguiendo [la guía de alumnos](docs/ALUMNOS.md). |
| `solucion/` | Ejemplo terminado para probar, comparar y continuar si te atascas. |

Las dos versiones usan `nucleo.py` y la misma `boveda/`. No copies solamente
`agente.py`: conserva la estructura del repositorio.

- [Guía de alumnos y retos](docs/ALUMNOS.md)
- [Preparación y guion del ponente](docs/PONENTE.md)
- [Mensaje previo para los alumnos](docs/PREPARACION.md)
- [Opciones de memoria, PDF y Canvas](docs/DECISIONES.md)
- [Registro de validación](docs/VALIDACION.md)

## Memoria que puedes abrir

```text
boveda/
  Inicio.md
  apuntes/       ← documentos .md que tú añades
  memoria/       ← notas que autorizas guardar
```

En [Obsidian](https://obsidian.md/), selecciona «Open folder as vault» y abre
`boveda`. También puedes usar cualquier editor. No necesitas plugins ni una cuenta.

Pide «Recuerda que quiero repasar OEE con ejemplos de fabricación». El programa
te muestra la nota y pregunta si quieres guardarla. Confirma con `s`.
Usa `/nuevo` o cierra y vuelve a abrir; las cuatro últimas notas se cargan desde disco.
Las anteriores siguen disponibles mediante la herramienta de búsqueda.
`/salir` termina. El historial de conversación vive en RAM y se descarta al cerrar.

Los archivos personales de `memoria/` están excluidos de Git. No publiques apuntes
privados al personalizar el repositorio: Git sí incluye `apuntes/`.

## Si algo falla

| Problema | Qué probar |
|---|---|
| `py` no existe | Prueba `python` en Windows; `python3` en macOS/Linux. |
| Ollama no responde | Abre la aplicación, o ejecuta `ollama serve` en otra terminal. |
| Falta el modelo | Ejecuta `ollama pull qwen3:4b-instruct`. |
| Error con herramientas | Actualiza Ollama y repite `--doctor`. |
| Va muy lento | Cierra otras aplicaciones, usa preguntas cortas o prueba el modelo menor. |
| La plantilla inventa respuestas | Aún no tiene herramientas conectadas: completa los TODO y observa la traza. |
| No encuentra un concepto | Busca palabras presentes en el documento; esta búsqueda no entiende sinónimos. |
| PDF no aparece en búsqueda | Esta versión lee solo Markdown. Lleva un texto breve convertido previamente. |

Alternativa ligera, que también debes ensayar porque puede usar peor las herramientas:

```sh
ollama pull qwen3:1.7b
```

```powershell
py solucion/agente.py --modelo qwen3:1.7b
```

Si no funciona la inferencia, puedes estudiar la búsqueda sin modelo:

```powershell
py solucion/agente.py --buscar "OEE Roble"
```

La salida anterior es una búsqueda determinista; no simula una respuesta del modelo.

## Comprobaciones del proyecto

```sh
python -m unittest discover -s tests -v
python herramientas/empaquetar.py
```

En Windows puedes sustituir `python` por `py`; en macOS/Linux, por `python3`.
El empaquetador crea `dist/taller-agente-local-ufv.zip` sin memoria personal,
configuración de Obsidian ni cachés. Las pruebas automáticas no necesitan Ollama.
El ensayo con modelo real se registra aparte en `docs/VALIDACION.md`.
