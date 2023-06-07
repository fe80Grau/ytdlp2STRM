from __main__ import app
from plugins.crunchyroll.crunchyroll import direct
from flask import Flask, stream_with_context, request, Response, send_from_directory, send_file, redirect
import json
import os


### TWITCH ZONE
#Redirect to best pre-merget format youtube url
@app.route("/crunchyroll/direct/<crunchyroll_id>")
def crunchyroll_direct(crunchyroll_id):
    return direct(crunchyroll_id)
