from flask import Flask
import time

#from flask_socketio import SocketIO, emit
from threading import Thread
app = Flask(__name__, template_folder='ui/html', static_folder='ui/static', static_url_path='')

from clases.config import config as c
from clases.folders import folders as f
from clases.cron import cron as cron
from clases.worker import worker as w
import config.routes



ytdlp2strm_config = c.config(
    './config/config.json'
).get_config()

def run_flask_app():
    app.run(host='0.0.0.0',port=ytdlp2strm_config['ytdlp2strm_port'],debug=False)


if __name__ == "__main__":
    # Crear una instancia de Cron
    crons = cron.Cron()
    crons.start()

    # Crear un hilo para clean_old_videos
    thread_clean_old_videos = Thread(
        target=f.folders().clean_old_videos
    )
    thread_clean_old_videos.daemon = True
    thread_clean_old_videos.start()

    # Crear un hilo para la aplicación Flask
    thread_flask_app = Thread(
        target=run_flask_app
    )
    thread_flask_app.daemon = True
    thread_flask_app.start()

    # Mantener el hilo principal activo
    while True:
        time.sleep(1)