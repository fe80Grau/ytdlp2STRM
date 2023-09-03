from __main__ import app
from plugins.crunchyroll.crunchyroll import direct

### CRUNCHY ZONE
@app.route("/crunchyroll/direct/<crunchyroll_id>")
def crunchyroll_direct(crunchyroll_id):
    return direct(crunchyroll_id)
