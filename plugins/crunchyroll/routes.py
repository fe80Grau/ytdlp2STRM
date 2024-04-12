from __main__ import app
from plugins.crunchyroll.crunchyroll import direct, download, remux

### CRUNCHY ZONE
@app.route("/crunchyroll/direct/<crunchyroll_id>")
def crunchyroll_direct(crunchyroll_id):
    return direct(crunchyroll_id)
#Download video and semd data throught http (serve video duration info, disk usage **clean_old_videos fucntion save your money)
@app.route("/crunchyroll/download/<crunchyroll_id>")
def crunchyroll_download(crunchyroll_id):
    return download(crunchyroll_id)
#experimental not works
@app.route("/crunchyroll/remux/<crunchyroll_id>")
def crunchyroll_remux(crunchyroll_id):
    return remux(crunchyroll_id)
