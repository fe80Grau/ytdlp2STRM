import os
import requests
import schedule
import time
import threading
from clases.config import config as c
from clases.worker import worker as w
from clases.log import log as l

config = c.config(
    './plugins/crunchyroll/config.json'
).get_config()

base_url = config['jellyfin_base_url']
api_key = config['jellyfin_api_key']
user_id = config['jellyfin_user_id']


# Inicializa un objeto Lock para el control de concurrencia
preload_lock = threading.Lock()

# Variable de cierre para controlar la ejecución concurrente de la función preload_video
is_preloading = False


def get_next_episode(serie_id, temporada_id, episodio_id):
    """Obtiene el ID del siguiente episodio basado en la ID actual del episodio."""
    url = f"{base_url}/Shows/{serie_id}/Episodes?seasonId={temporada_id}&userId={user_id}"
    headers = {'X-Emby-Token': api_key}
    response = requests.get(url, headers=headers)
    episodios = response.json().get('Items', [])
    
    episodio_actual_index = next((i for i, episodio in enumerate(episodios) if episodio['Id'] == episodio_id), None)

    if episodio_actual_index is not None and episodio_actual_index < len(episodios) - 1:
        siguiente_episodio = episodios[episodio_actual_index + 1]
        return siguiente_episodio['Id']
    else:
        return None
    
def fetch_item_details(item_id, user_id, api_key):
    url = f"{base_url}/Users/{user_id}/Items/{item_id}?api_key={api_key}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        log_text = (f"Error fetching item details: {response.status_code}")
        l.log("jellyfin", log_text)
        return None

def preload_video(item_id, user_id, api_key):
    item_details = fetch_item_details(item_id, user_id, api_key)
    if item_details is None:
        return
    file_content = item_details['MediaSources'][0].get("Path", "")
    if 'crunchyroll' in file_content:
        w.worker(file_content).preload()


def preload_next_episode():
    url = f"{base_url}/Sessions?api_key={api_key}"
    headers = {'X-Emby-Token': api_key}
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            sessions = response.json()
            
            for session in sessions:
                if session.get('NowPlayingItem') and session.get('NowPlayingItem').get('Type') == 'Episode':
                    now_playing = session.get('NowPlayingItem')
                    serie_id = now_playing.get('SeriesId')
                    temporada_id = now_playing.get('SeasonId')
                    episodio_id = now_playing.get('Id')
                    
                    siguiente_episodio_id = get_next_episode(serie_id, temporada_id, episodio_id)
                    
                    if siguiente_episodio_id:
                        preload_video(siguiente_episodio_id, user_id, api_key)
                        # Aquí puedes agregar la lógica para "precargar" el siguiente episodio
                    else:
                        pass
        else:
            log_text = (f"Error: El servidor devolvió un estado HTTP {response.status_code}")
            l.log("jellyfin", log_text)
    except requests.exceptions.RequestException as e:
        log_text = (f"Error HTTP: {e}")
        l.log("jellyfin", log_text)
    except ValueError as e:
        log_text = (f"Error JSON: {e}")
        l.log("jellyfin", log_text)

def daemon():
    """Inicia el daemon que verificará el estado de reproducción cada minuto."""
    if not base_url == "" \
    and not api_key == "" :
        while True:
            preload_next_episode()
            time.sleep(60)
