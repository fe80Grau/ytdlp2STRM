from __main__ import app
from plugins.youtube.youtube import direct, bridge, download
from flask import request, Response  # Importa request y Response desde Flask

### YOUTUBE ZONE
#Redirect to best pre-merget format youtube url
@app.route("/youtube/direct/<youtube_id>", methods=['GET', 'OPTIONS'])
def youtube_direct(youtube_id):
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        response = Response()
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Range, Content-Type'
        return response
    return direct(youtube_id, request.remote_addr)

#Redirect to best pre-merget format youtube url
@app.route("/youtube/bridge/<youtube_id>")
def youtube_bridge(youtube_id):
    return bridge(youtube_id)

#Keep URL from v0 version
@app.route("/youtube/redirect/<youtube_id>")
def youtube_redirect(youtube_id):
    return direct(youtube_id, request.remote_addr)


#Download video and semd data throught http (serve video duration info, disk usage **clean_old_videos fucntion save your money)
@app.route("/youtube/download/<youtube_id>")
def youtube_download(youtube_id):
    return download(youtube_id)
