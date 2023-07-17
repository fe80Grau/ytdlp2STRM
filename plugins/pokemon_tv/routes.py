from __main__ import app
from plugins.pokemon_tv.pokemon_tv import direct
from flask import Flask, stream_with_context, request, Response, send_from_directory, send_file, redirect
import json
import os



#Redirect to best pre-merget format youtube url
@app.route("/pokemon_tv/direct/<pokemon_tv_id>")
def pokemon_tv_direct(pokemon_tv_id):
    return direct(pokemon_tv_id)
