# MQTT: decisiones de una práctica ficticia

## Arquitectura de la maqueta

Un sensor publica medidas y un panel se suscribe a través de un broker MQTT.
Para nuestra maqueta usamos el topic `taller/linea-roble/temperatura`.
Publicamos una medida cada 5 segundos, con QoS 0 y retain desactivado.
Son decisiones del ejercicio; no pretenden definir los valores adecuados para cualquier sistema.

## Ampliación

Compara qué pasaría si el panel se conecta después de la última publicación.
Para estudiar QoS y retain en profundidad, consulta la especificación de MQTT.
El agente del taller no se conecta a ningún broker ni controla dispositivos.
