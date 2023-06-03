from __main__ import app
from plugins.twitch.twitch import direct
from flask import Flask, stream_with_context, request, Response, send_from_directory, send_file, redirect
import json
import os


### TWITCH ZONE
#Redirect to best pre-merget format youtube url
@app.route("/twitch/direct/<twitch_id>")
def twitch_direct(twitch_id):
    return direct(twitch_id)
