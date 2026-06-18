from __main__ import app
from plugins.twitch.twitch import direct, bridge
from flask import request  # Importa request desde Flask
from utils.validate_id import is_valid_media_id

### TWITCH ZONE
#Redirect to best pre-merget format youtube url
@app.route("/twitch/direct/<twitch_id>")
def twitch_direct(twitch_id):
    if not is_valid_media_id(twitch_id):
        return "Invalid id", 400
    return direct(twitch_id, request.remote_addr)

@app.route("/twitch/bridge/<twitch_id>")
def twitch_bridge(twitch_id):
    if not is_valid_media_id(twitch_id):
        return "Invalid id", 400
    return bridge(twitch_id)
