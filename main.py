import signal
import time
from threading import Thread, Event
from flask import Flask, request
app = Flask(__name__, template_folder='ui/html', static_folder='ui/static', static_url_path='')

from clases.config import config as c
from clases.folders import folders as f
from clases.cron import cron as cron
from clases.worker import worker as w
import config.routes

# Configuración global

def run_flask_app(stop_event, port):
    @app.before_request
    def before_request():
        if stop_event.is_set():
            print("Shutting down Flask server...")
            func = request.environ.get('werkzeug.server.shutdown')
            if func:
                func()
    
    try:
        app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
    except Exception as e:
        print(f"Exception in Flask app: {e}")
    print("Flask app stopped.")

def signal_handler(sig, frame):
    print('Signal received, terminating threads...')
    stop_event.set()

    if 'crons' in globals():
        crons.join()
        print("Cron thread terminated.")

    if 'thread_clean_old_videos' in globals():
        thread_clean_old_videos.join()
        print("Clean old videos thread terminated.")
    
    print('Threads and process terminated.')
    exit(0)

if __name__ == "__main__":
    ytdlp2strm_config = c.config('./config/config.json').get_config()
    stop_event = Event()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Crear una instancia de Cron con el evento de parada
    crons = cron.Cron(stop_event)
    crons.start()
    print(" * Crons thread started")

    # Crear una instancia de Folders y un hilo para clean_old_videos
    folders_instance = f.folders()
    thread_clean_old_videos = Thread(target=folders_instance.clean_old_videos, args=(stop_event,))
    thread_clean_old_videos.daemon = True
    thread_clean_old_videos.start()
    print(" * Clean old videos thread started")

    # Crear un proceso para la aplicación Flask
    port = ytdlp2strm_config['ytdlp2strm_port']
    run_flask_app(stop_event, port)

    try:
        # Mantener el hilo principal activo hasta que se establezca el evento de parada
        while not stop_event.is_set():
            time.sleep(1)
        
        # Esperar que todos los hilos y procesos terminen
        crons.join()
        print("Cron thread terminated.")

        thread_clean_old_videos.join()
        print("Clean old videos thread terminated.")

        print('Threads and process terminated.')
    
    except Exception as e:
        print(f"Exception in main loop: {e}")
    
    print("Exiting main.")
