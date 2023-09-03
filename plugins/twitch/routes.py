from __main__ import app
from plugins.twitch.twitch import direct

### TWITCH ZONE
#Redirect to best pre-merget format youtube url
@app.route("/twitch/direct/<twitch_id>")
def twitch_direct(twitch_id):
    return direct(twitch_id)
