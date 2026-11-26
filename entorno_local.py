"""Detección y perfiles prudentes. No cambia el sistema ni inicia servicios."""
import ctypes
import json
import os
import platform
import re
import shutil
import subprocess
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
AJUSTES = RAIZ / '.local' / 'ajustes.json'
LFM = 'lfm3:1.7b-q4_K_M'
RESPALDO = 'qwen3:4b-instruct'


def comando(argumentos):
    try:
        opciones = {'creationflags': subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {}
        return subprocess.check_output(argumentos, text=True, encoding='utf-8', errors='replace',
                                       timeout=12, stderr=subprocess.DEVNULL, **opciones).strip()
    except (OSError, subprocess.SubprocessError):
        return ''


def detectar():
    sistema, arquitectura = platform.system(), platform.machine().lower()
    total = disponible = 0
    if sistema == 'Windows':
        class Estado(ctypes.Structure):
            _fields_ = [('length', ctypes.c_ulong), ('load', ctypes.c_ulong)] + [
                (nombre, ctypes.c_ulonglong) for nombre in ('total', 'available', 'page', 'availpage', 'virtual', 'availvirtual', 'extended')]
        estado = Estado()
        estado.length = ctypes.sizeof(estado)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(estado)):
            total, disponible = estado.total, estado.available
    elif sistema == 'Darwin':
        texto = comando(['sysctl', '-n', 'hw.memsize'])
        total = int(texto) if texto.isdigit() else 0
        # macOS usa memoria unificada; reservamos al menos la mitad para sistema y apps.
        disponible = total // 2
    elif sistema == 'Linux':
        datos = {}
        try:
            for linea in Path('/proc/meminfo').read_text().splitlines():
                clave, valor = linea.split(':', 1)
                datos[clave] = int(valor.split()[0]) * 1024
            total, disponible = datos.get('MemTotal', 0), datos.get('MemAvailable', 0)
        except (OSError, ValueError):
            pass
    nvidia = shutil.which('nvidia-smi')
    if not nvidia and sistema == 'Windows':
        candidato = Path(os.environ.get('SystemRoot', 'C:/Windows')) / 'System32/nvidia-smi.exe'
        nvidia = str(candidato) if candidato.is_file() else None
    gpus = []
    if nvidia:
        datos = comando([nvidia, '--query-gpu=index,name,memory.total,memory.free,driver_version', '--format=csv,noheader,nounits'])
        for linea in datos.splitlines():
            partes = [p.strip() for p in linea.split(',')]
            if len(partes) == 5:
                try:
                    gpus.append({'indice': int(partes[0]), 'nombre': partes[1], 'vram_mb': int(float(partes[2])),
                                 'libre_mb': int(float(partes[3])), 'driver': partes[4], 'tipo': 'nvidia'})
                except ValueError:
                    continue
        # Algunas versiones de nvidia-smi no admiten compute_cap. Consultarlo
        # aparte conserva la detección de memoria y GPU en esos equipos.
        capacidades = comando([nvidia, '--query-gpu=index,compute_cap', '--format=csv,noheader,nounits'])
        por_indice = {gpu['indice']: gpu for gpu in gpus}
        for linea in capacidades.splitlines():
            partes = [p.strip() for p in linea.split(',')]
            if len(partes) != 2:
                continue
            try:
                indice, capacidad = int(partes[0]), float(partes[1])
            except ValueError:
                continue
            if indice in por_indice and 0 < capacidad < 100:
                por_indice[indice]['compute_capability'] = capacidad
    if sistema == 'Darwin' and arquitectura in ('arm64', 'aarch64'):
        gpus.append({'nombre': 'Apple Silicon / Metal (memoria unificada)', 'tipo': 'metal'})
    if not gpus and sistema == 'Windows':
        texto = comando(['powershell.exe', '-NoProfile', '-Command',
                         'Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name'])
        gpus = [{'nombre': linea, 'tipo': 'sin_verificar'} for linea in texto.splitlines() if linea]
    return {'sistema': sistema, 'arquitectura': arquitectura,
            'ram_gb': round(total / 1024**3, 2), 'ram_disponible_gb': round(disponible / 1024**3, 2),
            'gpu': gpus, 'cpu_hilos': os.cpu_count() or 1}


def perfil(hardware):
    avisos = []
    nvidia = sorted((g for g in hardware['gpu'] if g['tipo'] == 'nvidia'), key=lambda g: g['libre_mb'], reverse=True)
    acelerador, agentes, contexto = 'cpu', 1, 8192
    if nvidia:
        gpu = nvidia[0]
        libres = min(gpu['libre_mb'] + gpu.get('reclamable_taller_mb', 0), gpu['vram_mb'] - 1024)
        if libres >= 2500:
            acelerador = 'nvidia'
            agentes = 3 if libres >= 11000 else 2 if libres >= 6000 else 1
            contexto = 8192
        else:
            avisos.append('La GPU tiene poco margen libre; se propone un solo agente en CPU.')
    elif any(g['tipo'] == 'metal' for g in hardware['gpu']):
        acelerador = 'metal'
        agentes = 3 if hardware['ram_gb'] >= 32 else 2 if hardware['ram_gb'] >= 24 else 1
        contexto = 8192
    else:
        avisos.append('No se ha verificado aceleración NVIDIA/Metal. Perfil CPU conservador; AMD e Intel requieren comprobar el backend.')
    if hardware['ram_disponible_gb'] < 4:
        agentes, contexto = 1, 4096
        avisos.append('Queda poca RAM disponible. Cierra aplicaciones y vuelve a preparar el entorno.')
    return {'version': 3, 'modelo': RESPALDO, 'modelo_respaldo': LFM, 'acelerador': acelerador,
            'max_agentes': agentes, 'contexto': contexto, 'salida_tokens': 700,
            'timeout_segundos': 180, 'url': 'http://127.0.0.1:11435',
            'calibrado': False, 'hardware': hardware, 'avisos': avisos,
            'gpu_indice': nvidia[0]['indice'] if nvidia and acelerador == 'nvidia' else None}


def biblioteca_cuda(config):
    """Selecciona CUDA 12 para NVIDIA anteriores a Ampere en Windows.

    El backend CUDA 13 puede fallar durante conversaciones largas en estas
    tarjetas. No se fuerza una biblioteca en otros sistemas ni en GPU modernas.
    """
    hardware = config.get('hardware', {})
    if hardware.get('sistema') != 'Windows' or config.get('acelerador') != 'nvidia':
        return None
    gpu = next((gpu for gpu in hardware.get('gpu', [])
                if gpu.get('tipo') == 'nvidia' and gpu.get('indice') == config.get('gpu_indice')), None)
    if gpu is None:
        return None
    capacidad = gpu.get('compute_capability')
    if capacidad is not None:
        try:
            valor = float(capacidad)
        except (ValueError, TypeError):
            valor = 0
        if 0 < valor < 100:
            return 'cuda_v12' if valor < 8.0 else None
    # Respaldo limitado a familias inequívocas cuando el controlador no informa
    # de la capacidad. Evita inferir que una tarjeta desconocida es antigua.
    if re.search(r'\b(?:RTX\s*20\d{2}|GTX\s*(?:10|16)\d{2})\b', gpu.get('nombre', ''), re.IGNORECASE):
        return 'cuda_v12'
    return None


def guardar(configuracion):
    AJUSTES.parent.mkdir(exist_ok=True)
    temporal = AJUSTES.with_suffix('.tmp')
    temporal.write_text(json.dumps(configuracion, ensure_ascii=False, indent=2), encoding='utf-8')
    temporal.replace(AJUSTES)


def cargar():
    if not AJUSTES.exists():
        return {'modelo': RESPALDO, 'url': 'http://127.0.0.1:11434', 'contexto': 8192,
                'max_agentes': 1, 'salida_tokens': 700, 'timeout_segundos': 180}
    config = json.loads(AJUSTES.read_text(encoding='utf-8'))
    if not 1 <= config['max_agentes'] <= 3 or config['contexto'] not in (4096, 8192, 16384):
        raise ValueError('Configuración local inválida. Repite la preparación.')
    # El programa del taller solo acepta un servidor local.
    from urllib.parse import urlparse
    url = urlparse(config['url'])
    if url.scheme != 'http' or url.hostname not in ('localhost', '127.0.0.1') or url.path not in ('', '/'):
        raise ValueError('La dirección de Ollama debe ser local.')
    return config
