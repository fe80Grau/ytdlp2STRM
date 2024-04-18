from flask import Flask, request, Response, stream_with_context
from telethon import TelegramClient
import asyncio
import threading
from queue import Queue

# Configuraciones de Telethon
api_id = '123456'  # Sustituye por tu api_id
api_hash = 'abc123def456ghi789'  # Sustituye por tu api_hash

# Inicialización del cliente de Telegram
client = TelegramClient('session_name', api_id, api_hash)

app = Flask(__name__)

async def fetch_media(video_id):
    """Coroutina para obtener el mensaje con el video_id especificado"""
    await client.start()
    message = await client.get_messages('pokemontvcastellano', ids=video_id)
    return message

def download_generator(document, q):
    """Función productora para la descarga y transmisión del documento"""
    async def async_download():
        pos = 0
        async for chunk in client.iter_download(document, offset=pos):
            q.put(chunk)
            pos += len(chunk)
        q.put(None)  # Indicador de finalización
    
    def start_async_download():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(async_download())

    threading.Thread(target=start_async_download).start()
    while True:
        chunk = q.get()
        if chunk is None:
            break
        yield chunk

@app.route("/telegram/direct/<telegram_id>")
def telegram_direct(telegram_id):
    """Ruta de Flask para responder al pedido de transmisión de un video"""
    video_id = int(telegram_id)
    message = asyncio.run(fetch_media(video_id))  # Obtiene el mensaje
    if not message or not hasattr(message[0], 'media'):
        return "Mensaje no encontrado o no contiene media", 404
    document = message[0].media.document
    q = Queue()  # Cola para el generador
    return Response(stream_with_context(download_generator(document, q)), 
                    mimetype="video/mp4")

def run_telethon():
    """Función para ejecutar el cliente Telethon"""
    asyncio.run(client.start())

if __name__ == "__main__":
    # Inicia el cliente de Telethon en su hilo
    threading.Thread(target=run_telethon, daemon=True).start()
    # Ejecuta la aplicación Flask en el hilo principal
    app.run(port=5051, use_reloader=False)  # use_reloader=False para evitar conflictos con los hilos
