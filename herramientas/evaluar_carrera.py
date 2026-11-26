"""Evaluación real del modelo y OpenCode con una carrera ficticia, sin tocar apuntes personales."""
import argparse
import atexit
import base64
from datetime import date, timedelta
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import socket
import secrets
import sys
import tempfile
import threading
import time
import unicodedata
from urllib.request import Request, urlopen
from urllib.parse import urlencode

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
from academia import Academia


def normalizar(texto):
    return ''.join(c for c in unicodedata.normalize('NFD', texto.lower()) if not unicodedata.combining(c))


def pdf_prueba(ruta):
    from pypdf import PdfWriter
    from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
    escritor = PdfWriter()
    pagina = escritor.add_blank_page(width=600, height=800)
    fuente = DictionaryObject({NameObject('/Type'): NameObject('/Font'), NameObject('/Subtype'): NameObject('/Type1'), NameObject('/BaseFont'): NameObject('/Helvetica')})
    pagina[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): fuente})})
    flujo = DecodedStreamObject()
    flujo.set_data(b'BT /F1 12 Tf 50 700 Td (El sensor de ensayo QAZ47 tiene un limite de 7.4 bar.) Tj ET')
    pagina[NameObject('/Contents')] = escritor._add_object(flujo)
    with ruta.open('wb') as salida:
        escritor.write(salida)


def evaluar(proyecto, salida, casos_elegidos=None, configuracion_nueva=False, modelo=None, contexto=None):
    proyecto, salida = Path(proyecto).resolve(), Path(salida).resolve()
    config = json.loads((proyecto / '.local/ajustes.json').read_text(encoding='utf-8'))
    if modelo:
        config['modelo'] = modelo
    if contexto:
        config['contexto'] = contexto
    salida.mkdir(parents=True, exist_ok=True)
    espacio = Path(tempfile.mkdtemp(prefix='carrera-ficticia-', dir=salida))
    boveda = espacio / 'boveda'
    (boveda / 'apuntes').mkdir(parents=True)
    (boveda / 'memoria').mkdir()
    gestor = Academia(boveda)
    gestor.crear_curso('Tercero')
    for nombre in ('Automatizacion', 'Robotica'):
        gestor.crear_asignatura('Tercero', nombre)
    gestor.anadir_material('Tercero', 'Automatizacion', 'tema', 'Valvulas', 'Valvulas neumaticas y control de caudal.', 'Neumatica')
    gestor.anadir_material('Tercero', 'Automatizacion', 'apunte', 'Bomba P101', 'La bomba P101 trabaja a 3.2 bar. Antes de arrancar se abre la valvula V7.', 'Neumatica')
    entrega = (date.today() + timedelta(days=7)).isoformat()
    examen = (date.today() + timedelta(days=14)).isoformat()
    gestor.anadir_material('Tercero', 'Automatizacion', 'tarea', 'Practica PLC', 'Programar la secuencia de arranque.', 'PLC', entrega)
    adjunto = espacio / 'Banco de sensores.pdf'
    pdf_prueba(adjunto)
    hash_adjunto = hashlib.sha256(adjunto.read_bytes()).hexdigest()
    # El mismo importador que ejecuta el instalador, sin organización manual.
    from herramientas.importar_carpeta import importar
    originales = espacio / 'mis-documentos'
    (originales / 'Curso 1/Fisica').mkdir(parents=True)
    (originales / 'Curso 1/Fisica/Banco P77.md').write_text('En el banco P77 la masa de ensayo es 2.75 kg.', encoding='utf-8')
    (originales / 'General').mkdir()
    (originales / 'General/Tutorias.md').write_text('La tutoria de referencia THX21 es el martes a las 17:00.', encoding='utf-8')
    importar(originales, boveda)
    opencode = json.loads((proyecto / 'opencode.json').read_text(encoding='utf-8'))
    if configuracion_nueva:
        from herramientas import entorno
        raiz_previa, local_previo = entorno.RAIZ, entorno.LOCAL
        try:
            entorno.RAIZ, entorno.LOCAL = espacio, espacio / '.local'
            entorno.configurar_opencode(config)
            nueva = json.loads((espacio / 'opencode.json').read_text(encoding='utf-8'))
            nueva['mcp']['servers']['ufv-local']['command'] = [sys.executable, str(RAIZ / 'integraciones/servidor_mcp.py'), '--boveda', str(boveda), '--gestion-academica']
            nueva['mcp']['servers']['ufv-local']['cwd'] = str(RAIZ)
            opencode = nueva
        finally:
            entorno.RAIZ, entorno.LOCAL = raiz_previa, local_previo
    sistema = opencode['agents']['tutor']['system']
    opencode['agents']['tutor']['system'] = sistema.replace(proyecto.as_posix(), espacio.as_posix()).replace(str(proyecto), str(espacio))
    mcp = opencode['mcp']['servers']['ufv-local']
    mcp['command'][mcp['command'].index('--boveda') + 1] = str(boveda)
    # Captura solo parámetros de generación, nunca el contenido de mensajes.
    class ProxyDiagnostico(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            cuerpo = self.rfile.read(int(self.headers.get('Content-Length', '0')))
            datos = json.loads(cuerpo)
            meta = {k:datos.get(k) for k in ('model','stream','max_tokens','temperature','reasoning','reasoning_effort')}
            meta['herramientas'] = len(datos.get('tools', []))
            meta['nombres_herramientas'] = [h.get('function', {}).get('name') for h in datos.get('tools', [])]
            meta['mensajes'] = [{'rol': m.get('role'), 'caracteres': len(str(m.get('content', '')))} for m in datos.get('messages', [])]
            with (salida / 'parametros-api.jsonl').open('a', encoding='utf-8') as registro:
                registro.write(json.dumps(meta) + '\n')
            try:
                with urlopen(Request(config['url'] + self.path, data=cuerpo, headers={'Content-Type':'application/json'}),timeout=120) as respuesta:
                    self.send_response(respuesta.status)
                    self.send_header('Content-Type', respuesta.headers.get('Content-Type','application/json'))
                    self.end_headers()
                    while bloque := respuesta.read1(8192):
                        self.wfile.write(bloque)
                        self.wfile.flush()
            except (OSError, TimeoutError):
                self.close_connection = True

        def do_GET(self):
            try:
                with urlopen(config['url'] + self.path,timeout=15) as respuesta:
                    self.send_response(respuesta.status)
                    self.send_header('Content-Type', respuesta.headers.get('Content-Type','application/json'))
                    self.end_headers()
                    self.wfile.write(respuesta.read())
            except OSError:
                self.send_error(502)

    proxy = ThreadingHTTPServer(('127.0.0.1',0),ProxyDiagnostico)
    proxy.daemon_threads = True
    threading.Thread(target=proxy.serve_forever,daemon=True).start()
    opencode['providers']['ollama']['settings']['baseURL'] = f'http://127.0.0.1:{proxy.server_port}/v1'
    # La prueba permite acciones académicas en la bóveda ficticia, sin shell ni ediciones libres.
    opencode['permissions'] = [
        {'action': 'shell', 'resource': '*', 'effect': 'deny'},
        {'action': 'edit', 'resource': '*', 'effect': 'deny'},
        {'action': 'webfetch', 'resource': '*', 'effect': 'deny'},
        {'action': 'websearch', 'resource': '*', 'effect': 'deny'},
        {'action': 'external_directory', 'resource': '*', 'effect': 'deny'},
        {'action': 'read', 'resource': espacio.as_posix() + '/**', 'effect': 'allow'},
    ]
    (espacio / 'opencode.json').write_text(json.dumps(opencode, ensure_ascii=False, indent=2), encoding='utf-8')
    ambiente = dict(os.environ, OPENCODE_DB=str(espacio / 'sesiones.db'))

    def materiales():
        return gestor.materiales(gestor.asignatura('Tercero', 'Automatizacion'))

    def material(titulo):
        return next((m for m in materiales() if m['titulo'] == titulo), {})

    def asignatura_existe(curso, nombre):
        try:
            gestor.asignatura(curso, nombre)
            return True
        except ValueError:
            return False

    def tarea_correcta():
        m = material('Informe bombas')
        return m.get('tipo') == 'tarea' and m.get('tema') == 'Neumatica' and m.get('fecha') == entrega and 'Comparar presiones' in gestor.ruta(m['archivo']).read_text(encoding='utf-8')

    def pdf_correcto():
        m = material('Banco sensores')
        return bool(m.get('adjunto')) and '7.4 bar' in gestor.ruta(m['archivo']).read_text(encoding='utf-8') and hashlib.sha256(adjunto.read_bytes()).hexdigest() == hash_adjunto

    casos = [
        ('carpeta_importada', 'Segun mis apuntes de Fisica de Primero, cual es la masa de ensayo del banco P77? Cita la fuente.', ['buscar_apuntes', 'read'], ['2.75'], None),
        ('documento_general', 'Busca en mis documentos generales cuando es la tutoria de referencia THX21. Cita la fuente.', ['buscar_apuntes', 'read'], ['martes', '17:00'], None),
        ('asignaturas', 'Que asignaturas tengo en Tercero?', ['listar_carrera'], ['automatizacion', 'robotica'], None),
        ('materiales', 'Que temas, apuntes y tareas tengo de Automatizacion de Tercero? Una linea por material con su tipo y titulo, sin duplicados.', ['listar_carrera'], ['valvulas', 'bomba p101', 'practica plc'], None),
        ('pregunta_apuntes', 'Segun mis apuntes de Automatizacion de Tercero, a que presion trabaja la bomba P101 y que valvula debo abrir antes de arrancar? Cita la fuente.', ['buscar_apuntes', 'read'], ['3.2', 'v7'], None),
        ('asignatura_inexistente', 'Que materiales tengo en Termodinamica de Tercero? Si no existe en mi carrera, dimelo.', ['listar_carrera'], ['no'], lambda: not asignatura_existe('Tercero', 'Termodinamica')),
        ('crear_asignatura', 'Crea el curso Cuarto y, dentro de ese curso, crea la asignatura Control avanzado.', ['crear_curso', 'crear_asignatura'], [], lambda: asignatura_existe('Cuarto', 'Control avanzado')),
        ('anadir_tarea', f'Anade a Automatizacion de Tercero una tarea titulada Informe bombas, del tema Neumatica, con contenido Comparar presiones y fecha {entrega}.', ['anadir_material'], [], tarea_correcta),
        ('anadir_examen', f'Anade a Automatizacion de Tercero un examen titulado Parcial PLC, tema PLC, contenido Ladder y temporizadores, fecha {examen}.', ['anadir_material'], [], lambda: material('Parcial PLC').get('tipo') == 'examen' and material('Parcial PLC').get('fecha') == examen and material('Parcial PLC').get('tema') == 'PLC'),
        ('agenda', 'Que tareas y examenes pendientes tengo en Automatizacion de Tercero? Incluye fechas.', ['consultar_agenda'], ['practica plc', entrega], None),
        ('completar_tarea', 'Marca como completada la tarea Informe bombas de Automatizacion de Tercero. Consulta su ID si lo necesitas.', ['actualizar_tarea'], [], lambda: material('Informe bombas').get('estado') == 'completado'),
        ('importar_pdf', f'Importa el archivo local {adjunto} como apunte titulado Banco sensores del tema Sensores en Automatizacion de Tercero.', ['importar_material'], [], pdf_correcto),
        ('archivar_asignatura', 'Quita la asignatura Robotica de Tercero llevandola a la papelera, conservando sus materiales.', ['quitar_asignatura'], [], lambda: not asignatura_existe('Tercero', 'Robotica')),
        ('restaurar_asignatura', 'Restaura desde la papelera la asignatura Robotica de Tercero.', ['restaurar_asignatura'], [], lambda: asignatura_existe('Tercero', 'Robotica')),
    ]
    resultados = []
    # Desktop mantiene un servicio y espera a que el MCP esté conectado.
    # Reproducimos ese recorrido, sin compartir las sesiones del alumno.
    with socket.socket() as reserva:
        reserva.bind(('127.0.0.1', 0))
        puerto = reserva.getsockname()[1]
    endpoint = f'http://127.0.0.1:{puerto}'
    clave_api = secrets.token_urlsafe(24)
    ambiente['OPENCODE_SERVER_PASSWORD'] = clave_api
    autorizacion = 'Basic ' + base64.b64encode(('opencode:' + clave_api).encode()).decode()
    registro = (salida / 'opencode-servidor.log').open('w', encoding='utf-8')
    proceso_servidor = subprocess.Popen([config['opencode_bin'], 'serve', '--hostname', '127.0.0.1', '--port', str(puerto)],
                                       cwd=espacio, env=ambiente, stdout=registro, stderr=registro, stdin=subprocess.DEVNULL)

    def cerrar_servidor():
        import psutil
        try:
            principal = psutil.Process(proceso_servidor.pid)
            procesos = principal.children(recursive=True) + [principal]
            for p in reversed(procesos):
                try:
                    p.terminate()
                except psutil.NoSuchProcess:
                    pass
            psutil.wait_procs(procesos, timeout=3)
        except psutil.NoSuchProcess:
            pass
        registro.close()
    atexit.register(cerrar_servidor)
    for intento in range(60):
        try:
            peticion = Request(endpoint + '/api/mcp?' + urlencode({'directory': str(espacio)}), headers={'Authorization': autorizacion})
            with urlopen(peticion, timeout=2) as entrada:
                estado_mcp = json.load(entrada)
            if 'connected' in json.dumps(estado_mcp).lower():
                break
        except (OSError, ValueError):
            pass
        time.sleep(.5)
    else:
        raise RuntimeError('El MCP académico no se conectó; revisa opencode-servidor.log.')
    for nombre, pregunta, herramientas, fragmentos, verificar in casos:
        if casos_elegidos and nombre not in casos_elegidos:
            continue
        print('PROBANDO ' + nombre, flush=True)
        inicio = time.monotonic()
        try:
            r = subprocess.run([config['opencode_bin'], 'run', '--server', endpoint, '--auto', '--agent', 'tutor', '--format', 'json', '--archived', pregunta], cwd=espacio, env=ambiente, capture_output=True, text=True, encoding='utf-8', errors='replace', stdin=subprocess.DEVNULL, timeout=120)
            texto, error, codigo = r.stdout, r.stderr, r.returncode
        except subprocess.TimeoutExpired as exc:
            texto = (exc.stdout or b'').decode('utf-8', errors='replace') if isinstance(exc.stdout, bytes) else exc.stdout or ''
            error, codigo = 'Tiempo agotado (120 segundos)', -1
        (salida / (nombre + '.jsonl')).write_text(texto, encoding='utf-8')
        (salida / (nombre + '.stderr.log')).write_text(error, encoding='utf-8')
        eventos = []
        for linea in texto.splitlines():
            try:
                eventos.append(json.loads(linea))
            except ValueError:
                pass
        respuesta = '\n'.join(e.get('part', {}).get('text', '') for e in eventos if e.get('type') == 'text')
        llamadas = [e['part'] for e in eventos if e.get('type') == 'tool_use']
        completadas = [e.get('tool', '') for e in llamadas if e.get('state', {}).get('status') == 'completed']
        if nombre in ('pregunta_apuntes', 'carpeta_importada', 'documento_general'):
            herramientas = [*herramientas, 'grep']
        herramientas_ok = (any(any(t.endswith(h) for t in completadas) for h in herramientas) if nombre in ('pregunta_apuntes', 'carpeta_importada', 'documento_general') else all(any(t.endswith(h) for t in completadas) for h in herramientas))
        if nombre == 'asignatura_inexistente':
            herramientas_ok = herramientas_ok or any(t.get('tool', '').endswith('listar_carrera') and 'no existe' in normalizar(t.get('state', {}).get('error', '')) for t in llamadas)
        respuesta_ok = bool(respuesta.strip()) and all(normalizar(f) in normalizar(respuesta).replace('3,2', '3.2') for f in fragmentos)
        if nombre == 'materiales':
            lineas = normalizar(respuesta).splitlines()
            respuesta_ok = respuesta_ok and all(
                normalizar(respuesta).count(titulo) == 1 and any(tipo in linea and titulo in linea for linea in lineas)
                for tipo, titulo in [('tema', 'valvulas'), ('apunte', 'bomba p101'), ('tarea', 'practica plc')])
        try:
            estado_ok = bool(verificar()) if verificar else True
        except (ValueError, OSError, KeyError):
            estado_ok = False
        resultado = {'caso': nombre, 'ok': codigo == 0 and herramientas_ok and respuesta_ok and estado_ok, 'segundos': round(time.monotonic()-inicio, 2), 'codigo': codigo, 'herramientas_ok': herramientas_ok, 'respuesta_ok': respuesta_ok, 'estado_ok': estado_ok, 'llamadas': [{'herramienta': t.get('tool'), 'estado': t.get('state', {}).get('status'), 'argumentos': t.get('state', {}).get('input'), 'error': t.get('state', {}).get('error')} for t in llamadas], 'respuesta': respuesta}
        resultados.append(resultado)
        (salida / 'resultado.json').write_text(json.dumps({'modelo': config['modelo'], 'espacio_ficticio': str(espacio), 'resultados': resultados}, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps({k:resultado[k] for k in ('caso','ok','segundos','herramientas_ok','respuesta_ok','estado_ok')}, ensure_ascii=False), flush=True)
        if codigo == -1:
            break
    correctos = sum(r['ok'] for r in resultados)
    print(f'{correctos}/{len(resultados)} casos correctos. Informe: {salida / "resultado.json"}', flush=True)
    proxy.shutdown()
    proxy.server_close()
    cerrar_servidor()
    atexit.unregister(cerrar_servidor)
    return correctos == len(resultados)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--proyecto', type=Path, default=RAIZ)
    parser.add_argument('--salida', type=Path, default=RAIZ / '.local/evaluacion-carrera')
    parser.add_argument('--casos', nargs='+')
    parser.add_argument('--modelo', help='Modelo ya descargado que se quiere comparar, sin cambiar la instalación.')
    parser.add_argument('--contexto', type=int, choices=[4096, 8192, 16384])
    parser.add_argument('--configuracion-nueva', action='store_true', help='Usa las instrucciones actuales del repositorio en el espacio ficticio.')
    args = parser.parse_args()
    sys.exit(0 if evaluar(args.proyecto, args.salida, args.casos, args.configuracion_nueva, args.modelo, args.contexto) else 1)
