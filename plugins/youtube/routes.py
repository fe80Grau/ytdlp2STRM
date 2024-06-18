from __main__ import app
from plugins.youtube.youtube import direct, bridge, download, streams, remux_streams
from flask import request  # Importa request desde Flask

### YOUTUBE ZONE
#Redirect to best pre-merget format youtube url
@app.route("/youtube/direct/<youtube_id>")
def youtube_direct(youtube_id):
    return direct(youtube_id)

#Keep URL from v0 version
@app.route("/youtube/redirect/<youtube_id>")
def youtube_redirect(youtube_id):
    return direct(youtube_id)

#Keep URL from v0 version
@app.route("/youtube/stream/<media>/<youtube_id>")
def youtube_remux(media, youtube_id):
    return streams(media, youtube_id)

@app.route('/youtube/bridge/<youtube_id>')
def remux_youtube(youtube_id):
    start_time = request.args.get('start_time', default='0', type=str)
    end_time = request.args.get('end_time', default=None, type=str)
    return remux_streams(youtube_id, start_time, end_time)

#Download video and semd data throught http (serve video duration info, disk usage **clean_old_videos fucntion save your money)
@app.route("/youtube/download/<youtube_id>")
def youtube_download(youtube_id):
    return download(youtube_id)
