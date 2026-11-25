"""Compara el mismo GGUF con y sin DSpark; requiere llama-server y modelos locales.

No instala ni cambia el entorno normal del taller. Los servidores se limitan a localhost.
"""
import argparse
import concurrent.futures
import json
import os
from pathlib import Path
import statistics
import socket
import subprocess
import sys
import time
from urllib.request import Request, ProxyHandler, build_opener

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import nucleo

RAIZ = Path(__file__).resolve().parents[1]
HTTP = build_opener(ProxyHandler({}))
CASOS = [
    ('explicacion_es', 'Explica en español cómo usar MQTT para supervisar una línea industrial. Incluye un ejemplo de topic, QoS y tres errores habituales. Unas 180 palabras.', None),
    ('codigo', 'Write a Python function moving_average(values, window) and three assert examples. Explain its time complexity. Return about 180 words.', None),
    ('herramienta', 'Busca en mis apuntes el topic MQTT de nuestra maqueta.', 'buscar_apuntes'),
    ('calculo', 'Calcula el OEE usando la herramienta: 420 minutos planificados, 360 en marcha, 1000 piezas totales, 950 buenas y ciclo ideal de 18 segundos.', 'calcular_oee'),
]


def api(url, datos=None):
    peticion = Request(url, data=json.dumps(datos).encode() if datos is not None else None,
                       headers={'Content-Type': 'application/json'})
    with HTTP.open(peticion, timeout=60) as respuesta:
        return json.load(respuesta)


def consulta(url, caso, semilla):
    nombre, pregunta, esperada = caso
    datos = {'messages': [{'role': 'system', 'content': nucleo.INSTRUCCIONES},
                          {'role': 'user', 'content': pregunta}],
             'temperature': 0.1, 'top_k': 50, 'top_p': 1.0, 'min_p': 0,
             'repeat_penalty': 1.1, 'max_tokens': 256, 'seed': semilla,
             'cache_prompt': False, 'chat_template_kwargs': {'enable_thinking': False},
             'timings': True}
    if esperada:
        datos['tools'] = nucleo.HERRAMIENTAS
    inicio = time.monotonic()
    r = api(url + '/v1/chat/completions', datos)
    duracion = time.monotonic() - inicio
    mensaje = r['choices'][0]['message']
    llamadas = mensaje.get('tool_calls', [])
    nombres = [c['function']['name'] for c in llamadas]
    correcto = esperada in nombres if esperada else bool(mensaje.get('content'))
    argumentos_correctos = None
    if esperada == 'calcular_oee' and correcto:
        argumentos = next(c['function']['arguments'] for c in llamadas if c['function']['name'] == esperada)
        if isinstance(argumentos, str):
            argumentos = json.loads(argumentos)
        argumentos_correctos = argumentos == dict(zip(
            ('minutos_planificados', 'minutos_marcha', 'piezas_totales', 'piezas_buenas', 'ciclo_ideal_segundos'),
            (420, 360, 1000, 950, 18)))
    return {'caso': nombre, 'semilla': semilla, 'segundos': round(duracion, 4),
            'usage': r.get('usage'), 'timings': r.get('timings'), 'mensaje': mensaje,
            'comprobacion_basica': correcto, 'argumentos_oee_correctos': argumentos_correctos,
            'finish_reason': r['choices'][0]['finish_reason']}


def ejecutar(args):
    args.server = str(Path(args.server).resolve())
    with socket.socket() as puerto:
        puerto.bind(('127.0.0.1', args.puerto))
    salida = Path(args.salida)
    salida.parent.mkdir(parents=True, exist_ok=True)
    version = subprocess.run([args.server, '--version'], capture_output=True, text=True)
    informe = {'fecha': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
               'target': Path(args.target).name, 'draft': Path(args.draft).name,
               'repeticiones': args.repeticiones, 'contexto_total': 12288, 'slots': 3,
               'calentamiento': 'completo' if args.calentamiento_completo else 'consulta_breve',
               'max_tokens': 256, 'nota': 'Control local de rendimiento y estructura; no evalúa calidad general.',
               'gpu': subprocess.check_output(['nvidia-smi', '--query-gpu=name,driver_version,memory.total', '--format=csv,noheader'], text=True, timeout=10).strip(),
               'version': (version.stdout + version.stderr).strip(),
               'ejecuciones': []}
    for nombre, archivo in (('target_origen', args.target), ('draft_origen', args.draft)):
        manifiesto = Path(str(archivo) + '.json')
        if manifiesto.exists():
            informe[nombre] = json.loads(manifiesto.read_text(encoding='utf-8'))
    # Alternar el orden de configuraciones en cada repetición reduce el sesgo de calentamiento.
    configuraciones = args.bloques
    if 0 not in configuraciones or any(k not in (0, 2, 4, 8) for k in configuraciones):
        raise ValueError('Incluye 0 como referencia y bloques de 2, 4 u 8 tokens.')
    for repeticion in range(args.repeticiones):
        for k in configuraciones if repeticion % 2 == 0 else reversed(configuraciones):
            comando = [str(Path(args.server).resolve()), '-m', str(Path(args.target).resolve()),
                       '--host', '127.0.0.1', '--port', str(args.puerto), '-ngl', '99', '-fa', 'on',
                       '-c', '12288', '-np', '3', '--jinja', '--reasoning', 'off']
            if k:
                comando += ['-md', str(Path(args.draft).resolve()), '-ngld', '99',
                            '--spec-type', 'draft-dspark', '--spec-draft-n-max', str(k), '--spec-draft-n-min', '0']
            if args.device:
                comando += ['--device', args.device]
                if k:
                    comando += ['--spec-draft-device', args.device]
            registro = salida.parent / f'llama-{Path(args.target).stem}-r{repeticion}-k{k}.log'
            url = f'http://127.0.0.1:{args.puerto}'
            datos = {'repeticion': repeticion, 'draft_k': k,
                     'comando': [c.replace(str(RAIZ), '<repo>') for c in comando]}
            with registro.open('w', encoding='utf-8') as log:
                proceso = subprocess.Popen(comando, stdout=log, stderr=log,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
                try:
                    limite = time.monotonic() + 180
                    while True:
                        if proceso.poll() is not None:
                            raise RuntimeError(f'Servidor terminó: {registro}')
                        try:
                            api(url + '/health')
                            break
                        except Exception:
                            if time.monotonic() > limite:
                                raise TimeoutError(f'Servidor no arrancó: {registro}')
                            time.sleep(0.5)
                    consulta(url, ('warmup', 'Di hola.', None), 1)
                    if args.calentamiento_completo:
                        for caso in CASOS:
                            consulta(url, caso, 7)
                        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
                            list(pool.map(lambda caso: consulta(url, caso, 7), CASOS[:3]))
                    datos = {'repeticion': repeticion, 'draft_k': k,
                             'comando': [c.replace(str(RAIZ), '<repo>') for c in comando],
                             'serie': [consulta(url, caso, 42 + repeticion) for caso in CASOS]}
                    inicio = time.monotonic()
                    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
                        datos['paralelo'] = list(pool.map(lambda caso: consulta(url, caso, 42 + repeticion), CASOS[:3]))
                    datos['paralelo_segundos'] = round(time.monotonic() - inicio, 4)
                    datos['gpu_memoria_mib'] = subprocess.check_output(['nvidia-smi', '--query-gpu=memory.used', '--format=csv,noheader,nounits'], text=True, timeout=10).strip()
                    informe['ejecuciones'].append(datos)
                    salida.write_text(json.dumps(informe, ensure_ascii=False, indent=2), encoding='utf-8')
                    print(json.dumps({'repeticion': repeticion, 'k': k,
                        'serie_s': [d['segundos'] for d in datos['serie']],
                        'paralelo_s': datos['paralelo_segundos'],
                        'checks': [d['comprobacion_basica'] for d in datos['serie']] }), flush=True)
                except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as error:
                    datos['error'] = type(error).__name__ + ': ' + str(error)
                    informe['ejecuciones'].append(datos)
                    salida.write_text(json.dumps(informe, ensure_ascii=False, indent=2), encoding='utf-8')
                    print(json.dumps({'repeticion': repeticion, 'k': k, 'error': datos['error']}), flush=True)
                    return 1
                finally:
                    proceso.terminate()
                    try:
                        proceso.wait(timeout=15)
                    except subprocess.TimeoutExpired:
                        proceso.kill()
                        proceso.wait()
    for k in configuraciones:
        filas = [e for e in informe['ejecuciones'] if e['draft_k'] == k and 'error' not in e]
        if not filas:
            print(f'k={k}: ninguna ejecución completa; revisa los errores del informe.')
            continue
        print(f'k={k}: serie media {statistics.mean(sum(d["segundos"] for d in e["serie"]) for e in filas):.2f}s; '
              f'paralelo media {statistics.mean(e["paralelo_segundos"] for e in filas):.2f}s')
    return 1 if any('error' in e for e in informe['ejecuciones']) else 0


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--server', required=True)
    p.add_argument('--target', required=True)
    p.add_argument('--draft', required=True)
    p.add_argument('--repeticiones', type=int, default=2)
    p.add_argument('--puerto', type=int, default=11590)
    p.add_argument('--device', help='Ejemplo: CUDA0 o Vulkan1; comprobar con --list-devices.')
    p.add_argument('--bloques', nargs='+', type=int, default=[0, 2, 4, 8], help='0 desactiva DSpark.')
    p.add_argument('--calentamiento-completo', action='store_true', default=True,
                   help='Ejecuta toda la batería antes de cada medición (predeterminado).')
    p.add_argument('--calentamiento-breve', dest='calentamiento_completo', action='store_false',
                   help='Solo una consulta corta; puede incluir compilaciones tardías en los tiempos.')
    p.add_argument('--salida', default='dist/benchmark-dspark-q4.json')
    sys.exit(ejecutar(p.parse_args()))
