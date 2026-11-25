"""Instalación portable, servidor local, calibración y lanzador del taller."""
import argparse
import base64
import concurrent.futures
import hashlib
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tarfile
import time
import zipfile
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import ProxyHandler, Request, build_opener, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import entorno_local as entorno

RAIZ = entorno.RAIZ
LOCAL = RAIZ / '.local'
TOOLS = RAIZ / '.tools'
OLLAMA_VERSION = 'v0.40.18'
OPENCODE_VERSION = '2.4.1'
OLLAMA_SHA256 = {
    'ollama-darwin.tgz': '015261f434d31d7f0781f8ba6b59cc8e1f70ecb562a4e6db44dfdd5e02f7e562',
    'ollama-linux-amd64.tar.zst': 'b82649006cb5b54ed1237fa2d1a26a7f939a4fd03150033759acbff7ff315adf',
    'ollama-linux-arm64.tar.zst': '63f01dae3b65641866991e75e2aecb7aed8a4041f4c2c3c7d92862c5a47ebed6',
    'ollama-windows-amd64.zip': 'ca97292ac1e9acc77fcf473bb2741fa6acd12e3798f261b419680068b7cc4c16',
    'ollama-windows-arm64.zip': '671d27e9f93e14662f3941d705e4b3626fc05bd120055f160489c80c9c552912',
}


def json_web(url):
    with urlopen(Request(url, headers={'User-Agent': 'UFV-taller/0.2'}), timeout=40) as respuesta:
        return json.load(respuesta)


def descargar(url, destino, algoritmo, esperado):
    destino.parent.mkdir(parents=True, exist_ok=True)
    if destino.exists() and digest(destino, algoritmo) == esperado:
        return
    temporal = destino.with_suffix(destino.suffix + '.part')
    print(f'Descargando {destino.name}...', flush=True)
    with urlopen(Request(url, headers={'User-Agent': 'UFV-taller/0.2'}), timeout=90) as respuesta, temporal.open('wb') as salida:
        total, ultimo = 0, time.monotonic()
        while True:
            bloque = respuesta.read(1024 * 1024)
            if not bloque:
                break
            salida.write(bloque)
            total += len(bloque)
            if time.monotonic() - ultimo >= 8:
                print(f'  {total // 1024**2} MB descargados', flush=True)
                ultimo = time.monotonic()
    if digest(temporal, algoritmo) != esperado:
        raise RuntimeError(f'Checksum incorrecto: {destino.name}. Repite la preparación.')
    temporal.replace(destino)


def digest(archivo, algoritmo):
    calculo = hashlib.new(algoritmo)
    with archivo.open('rb') as entrada:
        for bloque in iter(lambda: entrada.read(1024 * 1024), b''):
            calculo.update(bloque)
    return calculo.hexdigest()


def extraer(archivo, destino):
    destino.mkdir(parents=True, exist_ok=True)
    raiz = destino.resolve()
    if archivo.suffix == '.zip':
        with zipfile.ZipFile(archivo) as paquete:
            for nombre in paquete.namelist():
                ruta = (destino / nombre).resolve()
                if ruta != raiz and raiz not in ruta.parents:
                    raise RuntimeError('El archivo comprimido contiene una ruta externa.')
            paquete.extractall(destino)
        return
    if archivo.suffix == '.zst':
        import zstandard
        with archivo.open('rb') as entrada, zstandard.ZstdDecompressor().stream_reader(entrada) as descomprimido:
            with tarfile.open(fileobj=descomprimido, mode='r|') as paquete:
                paquete.extractall(destino, filter='data')
        return
    with tarfile.open(archivo) as paquete:
        # uv instala Python 3.11 actualizado, con filtro seguro de extracción.
        paquete.extractall(destino, filter='data')


def instalar_ollama(hardware):
    instalado = shutil.which('ollama')
    if instalado:
        version = entorno.comando([instalado, '--version'])
        numeros = re.search(r'(\d+)\.(\d+)\.(\d+)', version)
        if numeros and tuple(map(int, numeros.groups())) >= (0, 40, 13):
            print('Se reutiliza el ejecutable de Ollama compatible; el servidor del taller será independiente.')
            return instalado
    sistema, arch = hardware['sistema'], hardware['arquitectura']
    arm = arch in ('arm64', 'aarch64')
    nombre = {'Windows': f"ollama-windows-{'arm64' if arm else 'amd64'}.zip",
              'Darwin': 'ollama-darwin.tgz',
              'Linux': f"ollama-linux-{'arm64' if arm else 'amd64'}.tar.zst"}.get(sistema)
    if not nombre:
        raise RuntimeError('Sistema no compatible con la instalación automática.')
    destino = TOOLS / 'ollama' / OLLAMA_VERSION
    marcador = destino / 'ejecutable.txt'
    if marcador.exists():
        binario = destino / marcador.read_text().strip()
        if binario.is_file():
            return str(binario)
    archivo = TOOLS / 'descargas' / nombre
    # Hashes publicados por GitHub para esta versión: evita consultar su API desde toda la clase.
    descargar(f'https://github.com/ollama/ollama/releases/download/{OLLAMA_VERSION}/{nombre}',
              archivo, 'sha256', OLLAMA_SHA256[nombre])
    extraer(archivo, destino)
    nombre_binario = 'ollama.exe' if sistema == 'Windows' else 'ollama'
    binario = next((a for a in destino.rglob(nombre_binario) if a.is_file()), None)
    if not binario:
        raise RuntimeError('No se encontró el ejecutable de Ollama en su distribución.')
    if sistema != 'Windows':
        binario.chmod(binario.stat().st_mode | 0o111)
    marcador.write_text(str(binario.relative_to(destino)), encoding='utf-8')
    return str(binario)


def instalar_opencode(hardware):
    sistema = {'Windows': 'windows', 'Darwin': 'darwin', 'Linux': 'linux'}.get(hardware['sistema'])
    if not sistema:
        raise RuntimeError('Sistema no compatible con OpenCode portable.')
    arch = 'arm64' if hardware['arquitectura'] in ('arm64', 'aarch64') else 'x64-baseline'
    paquete = f'@opencode/cli-{sistema}-{arch}'
    destino = TOOLS / 'opencode' / OPENCODE_VERSION
    nombre = 'opencode.exe' if sistema == 'windows' else 'opencode'
    candidatos = list(destino.rglob(nombre)) if destino.exists() else []
    if candidatos:
        return str(candidatos[0])
    metadatos = json_web(f'https://registry.npmjs.org/{quote(paquete, safe="@")}/{OPENCODE_VERSION}')
    dist = metadatos['dist']
    algoritmo, valor = dist['integrity'].split('-', 1)
    archivo = TOOLS / 'descargas' / f'opencode-{sistema}-{arch}-{OPENCODE_VERSION}.tgz'
    descargar(dist['tarball'], archivo, algoritmo, base64.b64decode(valor).hex())
    extraer(archivo, destino)
    binario = next((a for a in destino.rglob(nombre) if a.is_file()), None)
    if not binario:
        raise RuntimeError('No se encontró OpenCode en su paquete oficial.')
    if sistema != 'windows':
        binario.chmod(binario.stat().st_mode | 0o111)
    return str(binario)


def api(config, ruta, cuerpo=None, timeout=180):
    solicitud = Request(config['url'] + ruta,
                        data=None if cuerpo is None else json.dumps(cuerpo).encode(),
                        headers={'Content-Type': 'application/json'})
    try:
        with build_opener(ProxyHandler({})).open(solicitud, timeout=timeout) as respuesta:
            return json.load(respuesta)
    except HTTPError as error:
        detalle = error.read().decode('utf-8', errors='replace')[:400]
        raise RuntimeError(f'Ollama HTTP {error.code}: {detalle}') from error


def puerto_libre():
    for puerto in range(11435, 11446):
        with socket.socket() as comprobacion:
            try:
                comprobacion.bind(('127.0.0.1', puerto))
                return puerto
            except OSError:
                continue
    raise RuntimeError('No hay un puerto local libre entre 11435 y 11445.')


def servidor(config):
    import psutil
    estado = LOCAL / 'servidor.json'
    # Solo se reutiliza un servidor que el lanzador registró con el mismo perfil.
    clave = {k: config[k] for k in ('max_agentes', 'contexto', 'acelerador', 'gpu_indice')}
    if estado.exists():
        anterior = json.loads(estado.read_text(encoding='utf-8'))
        propio = None
        try:
            candidato = psutil.Process(anterior['pid'])
            if abs(candidato.create_time() - anterior['inicio']) < 0.01 and Path(candidato.exe()).resolve() == Path(anterior['binario']).resolve():
                propio = candidato
        except (psutil.Error, KeyError):
            pass
        if not propio and 'inicio' not in anterior:
            try:
                candidato = psutil.Process(anterior['pid'])
                if Path(candidato.exe()).resolve() == Path(config['ollama_bin']).resolve() and candidato.environ().get('OLLAMA_HOST') == anterior['url'].replace('http://', ''):
                    propio = candidato
            except psutil.Error:
                pass
        if propio and anterior['perfil'] == clave:
            prueba = dict(config, url=anterior['url'])
            try:
                api(prueba, '/api/version', timeout=3)
                config['url'] = anterior['url']
                return
            except (OSError, RuntimeError):
                pass
        if propio:
            # Solo termina el proceso registrado por este proyecto, comprobando identidad.
            procesos = propio.children(recursive=True) + [propio]
            for proceso in procesos:
                try:
                    proceso.terminate()
                except psutil.NoSuchProcess:
                    pass
            _, pendientes = psutil.wait_procs(procesos, timeout=10)
            if pendientes:
                raise RuntimeError('El servidor anterior del taller sigue ocupado. Cierra sus sesiones y vuelve a intentarlo.')
    config['url'] = f'http://127.0.0.1:{puerto_libre()}'
    ambiente = dict(os.environ, OLLAMA_HOST=config['url'].replace('http://', ''),
                    OLLAMA_NUM_PARALLEL=str(config['max_agentes']), OLLAMA_MAX_LOADED_MODELS='1',
                    OLLAMA_CONTEXT_LENGTH=str(config['contexto']), OLLAMA_MAX_QUEUE='16',
                    OLLAMA_NO_CLOUD='1', OLLAMA_KEEP_ALIVE='10m')
    if config['acelerador'] == 'nvidia':
        ambiente['CUDA_VISIBLE_DEVICES'] = str(config['gpu_indice'])
    elif config['acelerador'] == 'cpu':
        ambiente['CUDA_VISIBLE_DEVICES'] = '-1'
        ambiente['ROCR_VISIBLE_DEVICES'] = '-1'
        ambiente['OLLAMA_VULKAN'] = '0'
    opciones = {'creationflags': subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {'start_new_session': True}
    LOCAL.mkdir(exist_ok=True)
    with (LOCAL / 'ollama.log').open('ab') as registro:
        proceso = subprocess.Popen([config['ollama_bin'], 'serve'], env=ambiente, stdout=registro, stderr=registro, **opciones)
    for _ in range(60):
        if proceso.poll() is not None:
            raise RuntimeError('Ollama no pudo arrancar. Revisa .local/ollama.log y actualiza el controlador de la GPU si procede.')
        try:
            api(config, '/api/version', timeout=1)
            estado.write_text(json.dumps({'perfil': clave, 'url': config['url'], 'pid': proceso.pid,
                                         'inicio': psutil.Process(proceso.pid).create_time(), 'binario': config['ollama_bin']}), encoding='utf-8')
            return
        except (OSError, RuntimeError):
            time.sleep(0.5)
    proceso.terminate()
    raise RuntimeError('El servidor del taller no arrancó a tiempo.')


def descargar_modelo(config):
    if any(m.get('name') == config['modelo'] for m in api(config, '/api/tags')['models']):
        print(f"Modelo ya disponible: {config['modelo']}.", flush=True)
        return
    solicitud = Request(config['url'] + '/api/pull', data=json.dumps({'model': config['modelo'], 'stream': True}).encode(),
                        headers={'Content-Type': 'application/json'})
    print(f"Preparando modelo {config['modelo']}...", flush=True)
    ultimo = 0
    with build_opener(ProxyHandler({})).open(solicitud, timeout=600) as respuesta:
        for linea in respuesta:
            dato = json.loads(linea)
            if 'error' in dato:
                raise RuntimeError(dato['error'])
            if time.monotonic() - ultimo > 8 or dato.get('status') == 'success':
                progreso = f" {100 * dato.get('completed', 0) / dato['total']:.0f}%" if dato.get('total') else ''
                print('  ' + dato.get('status', '') + progreso, flush=True)
                ultimo = time.monotonic()


def calibrar(config):
    def una_prueba():
        inicio = time.monotonic()
        respuesta = api(config, '/api/chat', {
            'model': config['modelo'], 'stream': False, 'think': False,
            'messages': [{'role': 'user', 'content': 'Usa la herramienta eco con texto="listo". No respondas sin llamar a eco.'}],
            'tools': [{'type': 'function', 'function': {'name': 'eco', 'description': 'Devuelve el texto recibido.',
                       'parameters': {'type': 'object', 'properties': {'texto': {'type': 'string'}}, 'required': ['texto']}}}],
            'options': {'num_ctx': config['contexto'], 'num_predict': 128, 'temperature': 0.1}})
        llamadas = respuesta.get('message', {}).get('tool_calls', [])
        if not any(c.get('function', {}).get('name') == 'eco' for c in llamadas):
            raise RuntimeError('El modelo no produjo la llamada a herramienta esperada.')
        return round(time.monotonic() - inicio, 2)
    una_prueba()  # Carga inicial fuera de la medición en caliente.
    resultados = []
    maximo = config['max_agentes']
    for cantidad in range(1, maximo + 1):
        inicio = time.monotonic()
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=cantidad) as grupo:
                tiempos = list(grupo.map(lambda _: una_prueba(), range(cantidad)))
            resultados.append({'agentes': cantidad, 'ok': True, 'segundos': round(time.monotonic() - inicio, 2), 'peticiones': tiempos})
            print(f'  Prueba con {cantidad} tarea(s): correcta ({resultados[-1]["segundos"]} s).', flush=True)
            if cantidad > 1 and resultados[-1]['segundos'] > resultados[0]['segundos'] * cantidad * 1.35:
                config['max_agentes'] = cantidad - 1
                config['avisos'].append('Se redujo la concurrencia porque el lote tardó más que las tareas en serie con margen del 35 %.')
                break
        except (OSError, RuntimeError, ValueError) as error:
            resultados.append({'agentes': cantidad, 'ok': False, 'error': str(error)})
            if cantidad == 1:
                raise RuntimeError(f'Falló la prueba de inferencia/herramientas: {error}') from error
            config['max_agentes'] = cantidad - 1
            config['avisos'].append('Se redujo la concurrencia al fallar la calibración.')
            break
    cargados = api(config, '/api/ps')['models']
    modelo = next((m for m in cargados if m.get('name') == config['modelo'] or m.get('model') == config['modelo']), None)
    config['gpu_verificada'] = bool(modelo and modelo.get('size_vram', 0) > 0)
    if config['acelerador'] != 'cpu' and not config['gpu_verificada']:
        config['max_agentes'] = 1
        config['avisos'].append('La prueba no confirmó uso de GPU: se limita a un agente. Revisa drivers y .local/ollama.log.')
    config['calibrado'] = True
    config['calibracion'] = resultados


def configurar_opencode(config):
    # Workspace separado: no carga por accidente las instrucciones del ponente.
    espacio = LOCAL / 'estudio'
    espacio.mkdir(parents=True, exist_ok=True)
    boveda = (RAIZ / 'boveda').as_posix()
    ajustes = {
        '$schema': 'https://opencode.ai/config.json',
        'model': 'ollama/' + config['modelo'],
        'policies': [{'action': 'provider.use', 'resource': '*', 'effect': 'deny'},
                     {'action': 'provider.use', 'resource': 'ollama', 'effect': 'allow'}],
        'providers': {'ollama': {'settings': {'baseURL': config['url'] + '/v1'},
                                'models': {config['modelo']: {'limit': {'context': config['contexto'], 'output': config['salida_tokens']},
                                                            'body': {'reasoning_effort': 'none', 'max_tokens': config['salida_tokens']}}}}},
        'agents': {'tutor': {'description': 'Tutor de asignaturas con apuntes y memoria Markdown.', 'mode': 'primary',
                             'system': f'Responde en español. Consulta los apuntes en {boveda}/apuntes antes de responder sobre ellos. Cita archivo y líneas. '
                                       f'Lee {boveda}/memoria para recuperar notas previas. Solo guarda una nota Markdown en esa carpeta si el alumno lo pide. '
                                       'Si falta información, dilo. Da pistas antes de resolver ejercicios. No ejecutes comandos para contestar preguntas de estudio.',
                             'steps': 6}},
        'permissions': [{'action': 'shell', 'resource': '*', 'effect': 'ask'},
                        {'action': 'edit', 'resource': '*', 'effect': 'ask'},
                        {'action': 'webfetch', 'resource': '*', 'effect': 'deny'},
                        {'action': 'websearch', 'resource': '*', 'effect': 'deny'},
                        {'action': 'external_directory', 'resource': boveda + '/**', 'effect': 'allow'},
                        {'action': 'read', 'resource': boveda + '/**', 'effect': 'allow'}],
        'compaction': {'auto': True, 'keep': {'tokens': 1000}, 'buffer': '20%'}}
    (espacio / 'opencode.json').write_text(json.dumps(ajustes, ensure_ascii=False, indent=2), encoding='utf-8')
    return espacio


def probar_opencode(config):
    espacio = configurar_opencode(config)
    pregunta = 'Lee el archivo ' + (RAIZ / 'boveda/apuntes/MQTT.md').as_posix() + ' y responde solo con el topic MQTT de la maqueta.'
    ambiente = dict(os.environ, OPENCODE_DB=str(LOCAL / 'opencode.db'))
    opciones = {'creationflags': subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {}
    inicio = time.monotonic()
    print('Comprobando una lectura real desde OpenCode...', flush=True)
    try:
        resultado = subprocess.run([config['opencode_bin'], 'run', '--standalone', '--agent', 'tutor',
                                    '--format', 'json', '--archived', pregunta],
                                   cwd=espacio, env=ambiente, stdin=subprocess.DEVNULL, capture_output=True,
                                   timeout=180, **opciones)
        texto = resultado.stdout.decode('utf-8', errors='replace')
        (LOCAL / 'opencode-ensayo.jsonl').write_text(texto, encoding='utf-8')
        (LOCAL / 'opencode-ensayo.stderr.log').write_bytes(resultado.stderr)
        eventos = []
        for linea in texto.splitlines():
            try:
                eventos.append(json.loads(linea))
            except ValueError:
                continue
        respuesta = '\n'.join(e.get('part', {}).get('text', '') for e in eventos if e.get('type') == 'text')
        leido = any(e.get('type') == 'tool_use' and e.get('part', {}).get('tool') == 'read'
                    and e.get('part', {}).get('state', {}).get('status') == 'completed' for e in eventos)
        correcto = resultado.returncode == 0 and leido and 'taller/linea-roble/temperatura' in respuesta
    except subprocess.TimeoutExpired:
        correcto = False
    config['opencode_validado'] = correcto
    config['opencode_prueba_segundos'] = round(time.monotonic() - inicio, 2)
    config['interfaz'] = 'opencode' if correcto else 'terminal'
    if not correcto:
        config['avisos'].append('OpenCode no superó la lectura de prueba a tiempo. El arranque abrirá el agente Python; revisa .local/opencode-ensayo.*.')
    print('  Lectura de OpenCode: ' + ('correcta.' if correcto else 'se usará el recorrido Python.'), flush=True)


def preparar(args):
    hardware = entorno.detectar()
    estado = LOCAL / 'servidor.json'
    if estado.exists():
        import psutil
        try:
            anterior = json.loads(estado.read_text(encoding='utf-8'))
            proceso = psutil.Process(anterior['pid'])
            if abs(proceso.create_time() - anterior.get('inicio', -1)) < 0.01 and Path(proceso.exe()).resolve() == Path(anterior['binario']).resolve():
                cargados = api({'url': anterior['url']}, '/api/ps', timeout=3)['models']
                reclamable = sum(m.get('size_vram', 0) for m in cargados) // 1024**2
                for gpu in hardware['gpu']:
                    if gpu['tipo'] == 'nvidia' and gpu['indice'] == anterior['perfil'].get('gpu_indice'):
                        gpu['reclamable_taller_mb'] = reclamable
        except (OSError, ValueError, KeyError, RuntimeError, psutil.Error):
            pass
    config = entorno.perfil(hardware)
    print(json.dumps(config, ensure_ascii=False, indent=2), flush=True)
    if args.solo_detectar:
        return config
    if shutil.disk_usage(RAIZ).free < 7 * 1024**3:
        raise RuntimeError('Se recomiendan al menos 7 GB libres para descargas, extracción y modelo.')
    if not args.sin_obsidian:
        from herramientas.obsidian_local import instalar, registrar_boveda
        config['obsidian_bin'] = instalar(config['hardware'])
        registrar_boveda(config['hardware']['sistema'], config['obsidian_bin'], RAIZ / 'boveda')
    config['ollama_bin'] = instalar_ollama(config['hardware'])
    if not args.sin_opencode:
        config['opencode_bin'] = instalar_opencode(config['hardware'])
    servidor(config)
    descargar_modelo(config)
    info = api(config, '/api/show', {'model': config['modelo']})
    if 'tools' not in info.get('capabilities', []):
        raise RuntimeError('Ollama no declara soporte de herramientas para el modelo.')
    if not args.sin_calibrar:
        calibrar(config)
        # Aplica también al servidor una posible reducción del número de slots.
        servidor(config)
    configurar_opencode(config)
    if config.get('opencode_bin') and not args.sin_calibrar:
        probar_opencode(config)
    entorno.guardar(config)
    print(f"\nPreparado: {config['modelo']}, contexto {config['contexto']}, hasta {config['max_agentes']} agentes.\nConfiguración: .local/ajustes.json", flush=True)
    for aviso in config['avisos']:
        print('Nota: ' + aviso)
    return config


def main():
    for salida in (sys.stdout, sys.stderr):
        if hasattr(salida, 'reconfigure'):
            salida.reconfigure(encoding='utf-8', errors='replace')
    parser = argparse.ArgumentParser(description='Entorno automático UFV')
    parser.add_argument('accion', choices=['preparar', 'iniciar', 'equipo', 'doctor', 'terminal', 'notas'], default='iniciar', nargs='?')
    parser.add_argument('--solo-detectar', action='store_true')
    parser.add_argument('--sin-opencode', action='store_true')
    parser.add_argument('--sin-calibrar', action='store_true')
    parser.add_argument('--sin-obsidian', action='store_true')
    args = parser.parse_args()
    try:
        if args.accion == 'notas' and not args.solo_detectar:
            from herramientas.obsidian_local import instalar, abrir
            hardware = entorno.detectar()
            abrir(instalar(hardware), hardware['sistema'])
            return 0
        if args.accion == 'preparar' or not entorno.AJUSTES.exists() or args.solo_detectar:
            config = preparar(args)
            if args.solo_detectar or args.accion == 'preparar':
                return 0
        else:
            config = entorno.cargar()
            servidor(config)
            configurar_opencode(config)
            entorno.guardar(config)
        if args.accion == 'doctor':
            print(json.dumps({'configuracion': config, 'servidor': api(config, '/api/version'), 'cargados': api(config, '/api/ps')}, ensure_ascii=False, indent=2))
            return 0
        if args.accion == 'iniciar':
            if not args.sin_obsidian:
                from herramientas.obsidian_local import instalar, abrir
                config['obsidian_bin'] = instalar(config['hardware'])
                entorno.guardar(config)
                abrir(config['obsidian_bin'], config['hardware']['sistema'])
            if not config.get('opencode_bin') or config.get('interfaz') == 'terminal':
                print('Abriendo el agente Python del taller.')
                return subprocess.call([sys.executable, str(RAIZ / 'solucion/agente.py')], cwd=RAIZ)
            espacio = configurar_opencode(config)
            ambiente = dict(os.environ, OPENCODE_DB=str(LOCAL / 'opencode.db'))
            return subprocess.call([config['opencode_bin'], 'mini', '--standalone', '--agent', 'tutor'], cwd=espacio, env=ambiente)
        script = 'solucion/equipo.py' if args.accion == 'equipo' else 'solucion/agente.py'
        return subprocess.call([sys.executable, str(RAIZ / script)], cwd=RAIZ)
    except (OSError, RuntimeError, ValueError, StopIteration, subprocess.SubprocessError) as error:
        print(f'\nNo se completó la preparación: {error}\nPuedes consultar docs/ENTORNO.md o usar el arranque manual del README.')
        return 1
    except KeyboardInterrupt:
        print('\nPreparación interrumpida. Puedes volver a ejecutarla.')
        return 130


if __name__ == '__main__':
    sys.exit(main())
