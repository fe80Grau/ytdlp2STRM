# En tu archivo routes.py de Flask

import requests
from __main__ import app
from flask import Response, stream_with_context, request


@app.route("/telegram/direct/<telegram_id>")
def telegram_direct(telegram_id):
    quart_url = f"http://localhost:5151/telegram/direct/{telegram_id}"
    
    # Forward headers received from the original request (optional, but can be useful for things like range requests)
    headers = {}
    if 'Range' in request.headers:
        headers['Range'] = request.headers['Range']
    
    try:
        req = requests.get(quart_url, stream=True, headers=headers, timeout=None)  # timeout=None para esperar indefinidamente

        # En este punto, asumiendo que req.status_code es 200 o 206, pero deberías manejar otros códigos según sea necesario
        return Response(stream_with_context(req.iter_content(chunk_size=1024)), 
                        content_type=req.headers['Content-Type'],
                        status=req.status_code,
                        headers=dict(req.headers))  # Reenvía todos los headers de la respuesta de Quart
    except requests.RequestException as e:
        # Maneja los errores de la petición aquí (ej. log o retorno de un mensaje de error personalizado)
        return Response(f"Error al conectar con el servicio Quart: {e}", status=502)  # Bad Gateway para indicar un error upstrea