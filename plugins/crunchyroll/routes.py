from __main__ import app
from plugins.crunchyroll.crunchyroll import direct, download, streams, remux_streams
from utils.validate_id import is_valid_media_id

### CRUNCHY ZONE
@app.route("/crunchyroll/direct/<crunchyroll_id>")
def crunchyroll_direct(crunchyroll_id):
    if not is_valid_media_id(crunchyroll_id):
        return "Invalid id", 400
    return direct(crunchyroll_id)
#Download video and semd data throught http (serve video duration info, disk usage **clean_old_videos fucntion save your money)
@app.route("/crunchyroll/download/<crunchyroll_id>")
def crunchyroll_download(crunchyroll_id):
    if not is_valid_media_id(crunchyroll_id):
        return "Invalid id", 400
    return download(crunchyroll_id)
@app.route("/crunchyroll/stream/<media>/<crunchyroll_id>")
def crunchyroll_remux(media, crunchyroll_id):
    if not is_valid_media_id(media) or not is_valid_media_id(crunchyroll_id):
        return "Invalid id", 400
    return streams(media, crunchyroll_id)

@app.route('/crunchyroll/bridge/<crunchyroll_id>')
def remux(crunchyroll_id):
    if not is_valid_media_id(crunchyroll_id):
        return "Invalid id", 400
    return remux_streams(crunchyroll_id)
