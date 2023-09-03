from __main__ import app
from plugins.youtube.youtube import direct, bridge, download

### YOUTUBE ZONE
#Redirect to best pre-merget format youtube url
@app.route("/youtube/direct/<youtube_id>")
def youtube_direct(youtube_id):
    return direct(youtube_id)

#Keep URL from v0 version
@app.route("/youtube/redirect/<youtube_id>")
def youtube_redirect(youtube_id):
    return direct(youtube_id)

#Stream data directly throught http (no serve video duration info, no disk usage)
@app.route("/youtube/bridge/<youtube_id>")
def youtube_bridge(youtube_id):
    return bridge(youtube_id)

#Keep URL from v0 version
@app.route("/youtube/stream/<youtube_id>")
def youtube_stream(youtube_id):
    return bridge(youtube_id)

#Download video and semd data throught http (serve video duration info, disk usage **clean_old_videos fucntion save your money)
@app.route("/youtube/download/<youtube_id>")
def youtube_download(youtube_id):
    return download(youtube_id)
