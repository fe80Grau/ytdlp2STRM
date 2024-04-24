from flask import Flask

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
    crons = cron.Cron()
    crons.start()

    thread = Thread(
        target=f.folders().clean_old_videos
    )
    thread.daemon = True
    thread.start()
    
    run_flask_app()