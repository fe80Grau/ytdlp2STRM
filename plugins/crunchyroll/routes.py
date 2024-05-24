from __main__ import app
from plugins.crunchyroll.crunchyroll import direct, download, streams, remux_streams

### CRUNCHY ZONE
@app.route("/crunchyroll/direct/<crunchyroll_id>")
def crunchyroll_direct(crunchyroll_id):
    return direct(crunchyroll_id)
#Download video and semd data throught http (serve video duration info, disk usage **clean_old_videos fucntion save your money)
@app.route("/crunchyroll/download/<crunchyroll_id>")
def crunchyroll_download(crunchyroll_id):
    return download(crunchyroll_id)
@app.route("/crunchyroll/stream/<media>/<crunchyroll_id>")
def crunchyroll_remux(media, crunchyroll_id):
    return streams(media, crunchyroll_id)

@app.route('/crunchyroll/bridge/<crunchyroll_id>')
def remux(crunchyroll_id):
    return remux_streams(crunchyroll_id)
