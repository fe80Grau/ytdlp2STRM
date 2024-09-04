from __main__ import app
from plugins.twitch.twitch import direct, bridge
from flask import request  # Importa request desde Flask

### TWITCH ZONE
#Redirect to best pre-merget format youtube url
@app.route("/twitch/direct/<twitch_id>")
def twitch_direct(twitch_id):
    return direct(twitch_id, request.remote_addr)

@app.route("/twitch/bridge/<twitch_id>")
def twitch_bridge(twitch_id):
    return bridge(twitch_id)
