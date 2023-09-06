from flask import Flask, stream_with_context, request, Response, send_from_directory, send_file, redirect
from threading import Thread
app = Flask(__name__, template_folder='ui/html', static_folder='ui/static', static_url_path='')
from clases.config import config as c
from clases.folders import folders as f
import config.routes
from clases.cron import cron as cron

ytdlp2strm_config = c.config(
    './config/config.json'
).get_config()


if __name__ == "__main__":
    crons = cron.Cron()
    crons.start()

    thread = Thread(
        target=f.folders().clean_old_videos
    )
    thread.daemon = True
    thread.start()
    
    #Run Flask server
    app.run(host='0.0.0.0',port=ytdlp2strm_config['ytdlp2strm_port'],debug=True)
