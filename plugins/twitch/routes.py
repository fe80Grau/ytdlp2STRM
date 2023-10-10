from __main__ import app
from plugins.twitch.twitch import direct, bridge

### TWITCH ZONE
#Redirect to best pre-merget format youtube url
@app.route("/twitch/direct/<twitch_id>")
def twitch_direct(twitch_id):
    return direct(twitch_id)

@app.route("/twitch/bridge/<twitch_id>")
def twitch_bridge(twitch_id):
    return bridge(twitch_id)
