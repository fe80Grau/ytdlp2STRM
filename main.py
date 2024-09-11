import signal
import time
import logging
from threading import Thread, Event
from flask import Flask, request
app = Flask(__name__, template_folder='ui/html', static_folder='ui/static', static_url_path='')
from clases.config import config as c
from clases.folders import folders as f
from clases.log import log as l
from clases.cron import cron as cron
import config.routes

def run_flask_app(stop_event, port):
    @app.before_request
    def before_request():
        if stop_event.is_set():
            log_text = ("Shutting down Flask server...")
            l.log("main", log_text)

            func = request.environ.get('werkzeug.server.shutdown')
            if func:
                func()
    
    try:
        app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
    except Exception as e:
        log_text = (f"Exception in Flask app: {e}")
        l.log("main", log_text)

    log_text = ("Flask app stopped.")
    l.log("main", log_text)

def signal_handler(sig, frame):
    log_text = ('Signal received, terminating threads...')
    l.log("main", log_text)

    stop_event.set()
    
    log_text = ('Threads and process terminated.')
    l.log("main", log_text)
    exit(0)  # Using exit to ensure immediate termination

if __name__ == "__main__":
    ytdlp2strm_config = c.config('./config/config.json').get_config()
    stop_event = Event()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

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
    flask_thread = Thread(target=run_flask_app, args=(stop_event, port))
    flask_thread.daemon = True  # Set the thread as daemon
    flask_thread.start()
    log_text = (" * Flask thread started")
    l.log("main", log_text)

    try:
        # Mantener el hilo principal activo hasta que se establezca el evento de parada
        while not stop_event.is_set():
            time.sleep(1)

        log_text = ('Threads and process terminated.')
        l.log("main", log_text)

    except Exception as e:
        log_text = (f"Exception in main loop: {e}")
        l.log("main", log_text)

    log_text = ("Exiting main.")
    l.log("main", log_text)
