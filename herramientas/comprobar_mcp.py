"""Comprueba el transporte MCP, la búsqueda real y el cálculo sin usar el modelo."""
import json
import sys
from pathlib import Path


async def comprobar(raiz):
    from mcp import Client
    from mcp.client.stdio import StdioServerParameters
    raiz = Path(raiz).resolve()
    parametros = StdioServerParameters(command=sys.executable,
        args=[str(raiz / 'integraciones/servidor_mcp.py'), '--boveda', str(raiz / 'boveda'), '--gestion-academica'])
    async with Client(parametros, read_timeout_seconds=20) as cliente:
        herramientas = {t.name for t in (await cliente.list_tools()).tools}
        if not {'buscar_apuntes', 'calcular_oee', 'consultar_tutor_local'} <= herramientas:
            raise RuntimeError('Faltan herramientas del taller en el servidor MCP.')
        from academia import NOMBRES
        if not set(NOMBRES) <= herramientas:
            raise RuntimeError('Faltan herramientas de gestión de la carrera.')
        carrera = await cliente.call_tool('listar_carrera', {})
        if carrera.is_error:
            raise RuntimeError('No se puede leer la organización de la carrera.')
        busqueda = await cliente.call_tool('buscar_apuntes', {'consulta': 'MQTT maqueta'})
        if busqueda.is_error or 'taller/linea-roble/temperatura' not in str(busqueda.content):
            raise RuntimeError('MCP no puede consultar los apuntes de ejemplo.')
        resultado = await cliente.call_tool('calcular_oee', {
            'minutos_planificados': 420, 'minutos_marcha': 360, 'piezas_totales': 600,
            'piezas_buenas': 570, 'ciclo_ideal_segundos': 30})
        datos = json.loads(next(c.text for c in resultado.content if c.type == 'text'))
        if resultado.is_error or datos.get('oee_pct') != 67.8571:
            raise RuntimeError('El cálculo de prueba MCP no produjo el resultado esperado.')
    return {'ok': True, 'herramientas': sorted(herramientas), 'busqueda': True, 'oee_pct': datos['oee_pct']}
