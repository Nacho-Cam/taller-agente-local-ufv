"""Tres tareas independientes, con concurrencia acotada por el perfil local."""
import argparse
import concurrent.futures
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import nucleo
from solucion.agente import resolver_turno

TAREAS = [
    ('MQTT', 'Busca los apuntes MQTT y prepara dos preguntas de repaso con sus respuestas. Cita las fuentes.'),
    ('Sensores', 'Busca los apuntes del sensor P-101. Explica qué presión representa 12 mA y qué datos no conocemos. Cita la fuente.'),
    ('OEE', 'Busca los datos de la Línea Roble y calcula su OEE con la herramienta. Explica brevemente el resultado.'),
]


def ejecutar_equipo(boveda, workers):
    from nucleo import ejecutar_herramienta
    herramientas = [h for h in nucleo.HERRAMIENTAS_BASE if h['function']['name'] in ('buscar_apuntes', 'calcular_oee')]

    def solo_lectura(nombre, argumentos, raiz):
        if nombre not in ('buscar_apuntes', 'calcular_oee'):
            return {'guardado': False, 'motivo': 'El equipo trabaja en modo lectura.'}
        return ejecutar_herramienta(nombre, argumentos, raiz)

    def tarea(dato):
        tema, pregunta = dato
        inicio = time.monotonic()
        mensajes = [{'role': 'system', 'content': nucleo.INSTRUCCIONES + '\nTu tarea es independiente. No guardes memoria ni escribas archivos.'},
                    {'role': 'user', 'content': pregunta}]
        try:
            respuesta = resolver_turno(mensajes, nucleo.MODELO, boveda, herramientas=herramientas, ejecutar=solo_lectura)
            return {'tema': tema, 'respuesta': respuesta, 'segundos': round(time.monotonic() - inicio, 2)}
        except (RuntimeError, ValueError, OSError) as error:
            return {'tema': tema, 'error': str(error), 'segundos': round(time.monotonic() - inicio, 2)}
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as grupo:
        return list(grupo.map(tarea, TAREAS))


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    parser = argparse.ArgumentParser(description='Tres tareas locales independientes')
    parser.add_argument('--secuencial', action='store_true', help='Compara con un solo trabajador.')
    args = parser.parse_args()
    workers = 1 if args.secuencial else nucleo.CONFIG['max_agentes']
    print(f'Tres tareas; como máximo {workers} petición(es) simultánea(s).', flush=True)
    inicio = time.monotonic()
    resultados = ejecutar_equipo(nucleo.BOVEDA, workers)
    for resultado in resultados:
        print('\n' + resultado['tema'] + ':\n' + resultado.get('respuesta', resultado.get('error', '')))
    destino = nucleo.RAIZ / '.local' / 'equipo.json'
    destino.parent.mkdir(exist_ok=True)
    informe = {'modelo': nucleo.MODELO, 'max_agentes': workers,
               'segundos_total': round(time.monotonic() - inicio, 2), 'resultados': resultados}
    destino.write_text(json.dumps(informe, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'\nTiempo total: {informe["segundos_total"]} s. Informe: .local/equipo.json')
    return 1 if any('error' in r for r in resultados) else 0


if __name__ == '__main__':
    sys.exit(main())
