import requests
import html
import re
from PIL import Image
from io import BytesIO
from clases.folders import folders as f
from clases.log import log as l

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
            l.log("nfo", "Invalid NFO type.")
            return
        
        l.log("nfo", "Creating NFO file...")
        # Rellenar la plantilla con los datos proporcionados
        nfo_content = template.format(**self.nfo_data)

        # Crear el archivo NFO
        f.folders().write_file_spaces(
            f"{self.nfo_path}/{nfo_filename}", 
            nfo_content  # No uses nfo_content.strip()
        )
        # Descargar las imágenes correspondientes
        self.download_images(nfo_filename)

    def download_images(self, nfo_filename):
        try:
            if self.nfo_type == "tvshow":
                self.download_image(self.nfo_data['poster'], f"{self.nfo_path}/poster.png")
                self.download_image(self.nfo_data['landscape'], f"{self.nfo_path}/banner.png")
                self.download_image(self.nfo_data['landscape'], f"{self.nfo_path}/backdrop.png")
            elif self.nfo_type == "episode":
                image_url = self.nfo_data['preview']
                self.download_image(image_url, f"{self.nfo_path}/{nfo_filename.replace('.nfo','')}.png")
        except Exception as e:
            print(e)

    def download_image(self, url, path):
        try:
            response = requests.get(url)
            response.raise_for_status()  # Check if the request was successful
            
            # Convertir a PNG
            image = Image.open(BytesIO(response.content))
            png_image_path = path
            image.save(png_image_path, 'PNG')
            
            l.log("nfo", f"Image downloaded and converted to PNG: {path}")
        except requests.RequestException as e:
            l.log("nfo", f"Failed to download image from {url}: {e}")
        except Exception as e:
            l.log("nfo", f"Failed to convert image from {url} to PNG: {e}")

    tvshow_template = """<?xml version="1.0" encoding="UTF-8"?>
<tvshow>
    <title>{title}</title>
    <plot><![CDATA[{plot}]]></plot>
    <season>{season}</season>
    <episode>{episode}</episode>
    <thumb spoof="" cache="" aspect="landscape" preview="{landscape}">{landscape}</thumb>
    <thumb spoof="" cache="" aspect="poster" preview="{poster}">{poster}</thumb>
    <studio>{studio}</studio>
</tvshow>
    """

    movie_template = """<?xml version="1.0" encoding="UTF-8"?>
<movie>
    <title>{title}</title>
    <plot><![CDATA[{plot}]]></plot>
    <releasedate>{upload_date}</releasedate>
    <year>{year}</year>
    <thumb aspect="thumb" preview="{preview}">{preview}</thumb>
</movie>
    """

    episode_template = """<?xml version="1.0" encoding="UTF-8"?>
<episodedetails>
    <title>{title}</title>
    <plot><![CDATA[{plot}]]></plot>
    <releasedate>{upload_date}</releasedate>
    <year>{year}</year>
    <season>{season}</season>
    <episode>{episode}</episode>
    <thumb aspect="thumb" preview="{preview}">{preview}</thumb>
</episodedetails>
    """