from __main__ import app
from plugins.pokemon_tv.pokemon_tv import direct


@app.route("/pokemon_tv/direct/<pokemon_tv_id>")
def pokemon_tv_direct(pokemon_tv_id):
    return direct(pokemon_tv_id)
