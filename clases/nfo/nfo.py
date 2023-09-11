class nfo:
    def __init__(self, nfo_type, nfo_path, nfo_data):
        self.nfo_type = nfo_type
        self.nfo_path = nfo_path
        self.nfo_data = nfo_data

    def make_nfo(self):
        # Verificar el tipo de NFO
        if self.nfo_type == "tvshow":
            template = self.tvshow_template
            nfo_filename = "tvshow.nfo"
        elif self.nfo_type == "movie":
            template = self.movie_template
            nfo_filename = f"{self.nfo_data['item_name']}.nfo"
        elif self.nfo_type == "episode":
            template = self.episode_template
            nfo_filename = f"{self.nfo_data['item_name']}.nfo"
        else:
            print("Invalid NFO type.")
            return

        # Rellenar la plantilla con los datos proporcionados
        nfo_content = template.format(**self.nfo_data)

        # Crear el archivo NFO
        with open(f"{self.nfo_path}/{nfo_filename}", "w", encoding="utf-8") as nfo_file:
            nfo_file.write(nfo_content.strip())


    tvshow_template = """
    <?xml version="1.0" encoding="UTF-8"?>
        <tvshow>
            <title>{title}</title>
            <plot>{plot}</plot>
            <season>{season}</season>
            <episode>{episode}</episode>
            <thumb spoof="" cache="" aspect="landscape" preview="{landscape}">{landscape}</thumb>
            <thumb spoof="" cache="" aspect="poster" preview="{poster}">{poster}</thumb>
            <studio>{studio}</studio>
            <!-- Agregar más campos según sea necesario -->
        </tvshow>
    """

    movie_template = """
    <?xml version="1.0" encoding="UTF-8"?>
        <movie>
            <title>{title}</title>
            <plot>{plot}</plot>
            <genre>{genre}</genre>
            <!-- Agregar más campos según sea necesario -->
        </movie>
    """

    episode_template = """
    <?xml version="1.0" encoding="UTF-8"?>
        <episodedetails>
            <title>{title}</title>
            <plot>{plot}</plot>
            <season>{season}</season>
            <episode>{episode}</episode>
            <thumb aspect="thumb" preview="{preview}">{preview}</thumb>
        </episodedetails>
    """