from __main__ import app
from plugins.youtube.main import direct, bridge, download
from flask import Flask, stream_with_context, request, Response, send_from_directory, send_file, redirect
import json

#Reading config file
with open(
        './plugins/youtube/config.json', 
        'r'
    ) as f:
    config = json.load(f)


### YOUTUBE ZONE
#Redirect to best pre-merget format youtube url
@app.route("/youtube/direct/<youtube_id>")
def youtube_direct(youtube_id):
    return direct(youtube_id)

#Stream data directly throught http (no serve video duration info, no disk usage)
@app.route("/youtube/bridge/<youtube_id>")
def youtube_bridge(youtube_id):
    return bridge(youtube_id)

#Download video and semd data throught http (serve video duration info, disk usage **clean_old_videos fucntion save your money)
@app.route("/youtube/download/<youtube_id>")
def youtube_download(youtube_id):
    return download(youtube_id)
