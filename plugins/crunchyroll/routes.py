from __main__ import app, request
from plugins.crunchyroll.crunchyroll import direct, download

### CRUNCHY ZONE
@app.route("/crunchyroll/direct/<crunchyroll_id>")
def crunchyroll_direct(crunchyroll_id):
    return direct(crunchyroll_id)
#Download video and semd data throught http (serve video duration info, disk usage **clean_old_videos fucntion save your money)
@app.route("/crunchyroll/download/<crunchyroll_id>")
def crunchyroll_download(crunchyroll_id):
    return download(crunchyroll_id)
