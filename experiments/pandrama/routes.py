from __main__ import app
from plugins.sx3.sx3 import bridge, direct
from flask import Flask, stream_with_context, request, Response, send_from_directory, send_file, redirect
import json
import os


### TWITCH ZONE
#Redirect to best pre-merget format youtube url
@app.route("/episodio/oh-mi-venus-t1-capitulo-1/")
def pandrama():
    return send_from_directory('plugins/pandrama','test.html')

