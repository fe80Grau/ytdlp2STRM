import signal
import time
import logging
import os
import sys
from threading import Thread, Event
from flask import Flask, request
app = Flask(__name__, template_folder='ui/html', static_folder='ui/static', static_url_path='')
from clases.config import config as c
from clases.folders import folders as f
from clases.log import log as l
from clases.cron import cron as cron

# Variables globales para controlar el reinicio y parada
restart_flag = False
stop_event = None

def run_flask_app(stop_event, port, host='0.0.0.0'):
    @app.before_request
    def before_request():
        if stop_event.is_set():
            log_text = ("Shutting down Flask server...")
            l.log("main", log_text)

            func = request.environ.get('werkzeug.server.shutdown')
            if func:
                func()
    
    try:
        socketio.run(app, host=host, port=port, debug=False, use_reloader=False, allow_unsafe_werkzeug=True)
    except Exception as e:
        log_text = (f"Exception in Flask app: {e}")
        l.log("main", log_text)

    log_text = ("Flask app stopped.")
    l.log("main", log_text)

def signal_handler(sig, frame):
    global stop_event
    log_text = ('Signal received, terminating threads...')
    l.log("main", log_text)

    stop_event.set()
    
    log_text = ('Threads and process terminated.')
    l.log("main", log_text)
    exit(0)  # Using exit to ensure immediate termination

def restart_application():
    """Reinicia la aplicación usando os.execv()"""
    global restart_flag, stop_event
    restart_flag = True
    log_text = ('Restart requested, stopping threads...')
    l.log("main", log_text)
    stop_event.set()

if __name__ == "__main__":
    ytdlp2strm_config = c.config('./config/config.json').get_config()
    stop_event = Event()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Importar rutas después de inicializar variables globales
    import config.routes
    from ui.routes import socketio

    # Crear una instancia de Cron con el evento de parada
    crons = cron.Cron(stop_event)
    crons.start()
    log_text = (" * Crons thread started")
    l.log("main", log_text)

    # Crear una instancia de Folders y un hilo para clean_old_videos
    folders_instance = f.folders()
    thread_clean_old_videos = Thread(target=folders_instance.clean_old_videos, args=(stop_event,))
    thread_clean_old_videos.daemon = True  # Set the thread as daemon
    thread_clean_old_videos.start()
    log_text = (" * Clean old videos thread started")
    l.log("main", log_text)

    # Crear un proceso para la aplicación Flask
    port = ytdlp2strm_config['ytdlp2strm_port']
    # Respeta el host configurado (p. ej. 127.0.0.1 para no exponer la UI a la
    # red). Si no esta definido, se mantiene el comportamiento previo (0.0.0.0).
    host = ytdlp2strm_config.get('ytdlp2strm_host', '0.0.0.0')
    flask_thread = Thread(target=run_flask_app, args=(stop_event, port, host))
    flask_thread.daemon = True  # Set the thread as daemon
    flask_thread.start()
    log_text = (" * Flask thread started")
    l.log("main", log_text)

    try:
        # Mantener el hilo principal activo hasta que se establezca el evento de parada
        while not stop_event.is_set():
            if not crons.is_alive():
                l.log("main", "Crons thread is not alive. Restarting it.")
                crons = cron.Cron(stop_event)
                crons.start()
                l.log("main", " * Crons thread restarted")
            time.sleep(1)

        log_text = ('Threads and process terminated.')
        l.log("main", log_text)

    except Exception as e:
        log_text = (f"Exception in main loop: {e}")
        l.log("main", log_text)

    # Si se solicitó reinicio, ejecutar el reinicio
    if restart_flag:
        log_text = ("Restarting application...")
        l.log("main", log_text)
        time.sleep(1)  # Dar tiempo para que los logs se escriban
        python = sys.executable
        os.execv(python, [python] + sys.argv)
    else:
        log_text = ("Exiting main.")
        l.log("main", log_text)
