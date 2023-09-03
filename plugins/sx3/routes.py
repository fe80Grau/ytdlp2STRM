from __main__ import app
from plugins.sx3.sx3 import bridge, direct


#Redirect to best pre-merget format youtube url
@app.route("/sx3/bridge/<sx3_id>")
def sx3_bridge(sx3_id):
    return bridge(sx3_id)


#Redirect to best pre-merget format youtube url
@app.route("/sx3/direct/<sx3_id>")
def sx3_direct(sx3_id):
    return direct(sx3_id)
