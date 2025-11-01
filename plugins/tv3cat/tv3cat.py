import requests
from bs4 import BeautifulSoup
import json
import os
from clases.config import config as c
from clases.worker import worker as w
from clases.folders import folders as f
from clases.nfo import nfo as n
from clases.log import log as l
from utils.sanitize import sanitize

class tv3cat:
    def __init__(self, channel=False):
        self.channel = channel
        # Uso de las funciones
        program_id, seasons = self.fetch_program_id_and_seasons()

        if program_id and seasons:
            self.episodes = self.fetch_json_data(program_id, seasons)
            self.channel_name = self.episodes[0]['programa']
        else:
            log_text = ("No se pudo extraer el programId o las temporadas.")
            l.log("tv3cat", log_text)
        return None

    def recursively_find_key_value(self, obj, key, value):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k == key and v == value:
                    return obj
                else:
                    found = self.recursively_find_key_value(v, key, value)
                    if found:
                        return found
        elif isinstance(obj, list):
            for item in obj:
                found = self.recursively_find_key_value(item, key, value)
                if found:
                    return found
        return None

    def fetch_program_id_and_seasons(self):
        url = self.channel
        response = requests.get(url)
        seasons = []

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            script = soup.find('script', id='__NEXT_DATA__')
            if script:
                data = json.loads(script.string)
                temp_data = self.recursively_find_key_value(data, 'tipus', 'temporades')
                if temp_data and 'items' in temp_data:
                    seasons_info = temp_data['items']
                    try:
                        final_season_number = int(seasons_info.split('_')[-1])
                    except:
                        final_season_number = 1

                    seasons = [f'PUTEMP_{i}' for i in range(1, final_season_number + 1)]
                    
                    program_id = data.get('props', {}).get('pageProps', {}).get('headers', {}).get('Surrogate-Key').split('programatv_id=')[1].split('&')[0]
                    return program_id, seasons
        return None, []

    def get_video_url(self, video_id, base_path=None):
        url = f"https://api-media.ccma.cat/pvideo/media.jsp?media=video&versio=vast&idint={video_id}&profile=pc_3cat&format=dm"
        response = requests.get(url)
        if response.status_code == 200:
            json_data = response.json()
            video_url = json_data.get('media', {}).get('url', [])[0].get('file')
            
            # Obtener subtítulos VTT
            subtitles_url = None
            for subtitle in json_data.get('subtitols', []):
                if subtitle.get('format') == 'vtt':
                    subtitles_url = subtitle.get('url')
                    break
            
            if subtitles_url and base_path:
                try:
                    # Descargar el archivo VTT
                    vtt_response = requests.get(subtitles_url)
                    if vtt_response.status_code == 200:
                        # Usar la misma ruta que el STRM pero con extensión .vtt
                        vtt_filename = base_path.replace('.strm', '.vtt')
                        # Asegurarnos que el directorio existe
                        vtt_dir = os.path.dirname(vtt_filename)
                        if not os.path.exists(vtt_dir):
                            os.makedirs(vtt_dir)
                        with open(vtt_filename, 'wb') as vtt_file:
                            vtt_file.write(vtt_response.content)
                except Exception as e:
                    l.log("tv3cat", f"Error al descargar subtítulos: {str(e)}")
            
            return video_url
        return None

    def fetch_json_data(self, program_id, seasons):
        episodes = []
        url = f"https://www.3cat.cat/api/3cat/dades/?queryKey=%5B%22tira%22%2C%7B%22url%22%3A%22%2F%2Fapi.3cat.cat%2Fvideos%3F_format%3Djson%26ordre%3D-capitol%26origen%3Dllistat%26programatv_id%3D{program_id}%26tipus_contingut%3DPPD%26items_pagina%3D1000%26pagina%3D1%26sdom%3Dimg%26version%3D2.0%26cache%3D180%26https%3Dtrue%26master%3Dyes%26ordre%3Dcapitol%26temporada%3D%26ordre%3Dcapitol%26temporada%3D%22%7D%5D"
        response = requests.get(url)
        
        if response.status_code == 200:
            json_data = response.json()
            items = json_data.get('resposta', {}).get('items', {}).get('item', [])
            for item in items:
                try:
                    temporada = item.get('temporades',[])[0].get('id').split('_')[1]
                except:
                    temporada = 1
                
                video_id = item.get('id')
                capitulo = item.get('capitol_temporada') if item.get('capitol_temporada') > 0 else item.get('capitol')
                titulo = item.get('permatitle')
                programa = item.get('programa')
                
                # Solo procesar si hay número de capítulo
                if capitulo > 0:
                    video_url = self.get_video_url(video_id)
                    
                    episode_data = {
                        'id': video_id,
                        'titulo': titulo,
                        'capitulo': capitulo,
                        'temporada': temporada,
                        'programa': programa,
                        'video_url': video_url
                    }
                    episodes.append(episode_data)
                if episode_data['capitulo'] > 0:
                    episodes.append(episode_data)
        return episodes



## -- LOAD CONFIG AND CHANNELS FILES
ytdlp2strm_config = c.config(
    './config/config.json'
).get_config()

config = c.config(
    './plugins/tv3cat/config.json'
).get_config()

channels = c.config(
    config["channels_list_file"]
).get_channels()
media_folder = config["strm_output_folder"]

def to_strm(method):
    for tv3cat_channel in channels:
        log_text = (f'Working {tv3cat_channel}...')
        l.log("tv3cat", log_text)
        tv3 = tv3cat(tv3cat_channel)
        if tv3.episodes:
            # -- MAKES CHANNEL DIR (AND SUBDIRS) IF NOT EXIST, REMOVE ALL STRM IF KEEP_OLDER_STRM IS SETTED TO FALSE IN GENERAL CONFIG
            f.folders().make_clean_folder(
                "{}/{}".format(
                    media_folder,  
                    sanitize(
                        "{}".format(
                            tv3.channel_name
                        )
                    )
                ),
                False,
                config
            )

            for episode in tv3.episodes:
                video_name = "{} - {}".format(
                    "S{}E{}".format(
                        str(episode['temporada']).zfill(2), 
                        str(episode['capitulo']).zfill(2),
                    ),
                    episode['titulo']
                )

                file_content = episode['video_url']
                file_path = "{}/{}/{}/{}.{}".format(
                    media_folder,  
                    sanitize(
                        "{}".format(
                            tv3.channel_name
                        )
                    ),  
                    sanitize(
                        "S{}".format(
                            str(episode['temporada']).zfill(2)
                        )
                    ), 
                    sanitize(video_name), 
                    "strm"
                )

                # Crear directorio si no existe
                episode_dir = "{}/{}/{}".format(
                    media_folder,  
                    sanitize(
                        "{}".format(
                            tv3.channel_name
                        )
                    ),  
                    sanitize(
                        "S{}".format(
                            str(episode['temporada']).zfill(2)
                        )
                    )
                )
                f.folders().make_clean_folder(episode_dir, False, config)

                # Escribir archivo STRM
                f.folders().write_file(file_path, file_content)
                
                # Descargar subtítulos si están disponibles
                tv3.get_video_url(episode['id'], file_path)