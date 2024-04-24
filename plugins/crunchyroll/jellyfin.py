import os
import requests
import schedule
import time
import threading
from clases.config import config as c

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
        print(f"Error fetching item details: {response.status_code}")
        return None

def preload_video(item_id, user_id, api_key):
    global is_preloading
    
    # Intenta adquirir el Lock
    if not preload_lock.acquire(blocking=False):
        # Si no se puede adquirir el Lock, significa que otra instancia ya está ejecutando preload_video
        #print("Ya se está precargando un video.")
        return
    
    # Verifica si ya se está ejecutando la función
    if is_preloading:
        #print("Ya se está precargando otro video. Saliendo...")
        preload_lock.release()  # No olvides liberar el Lock si decides no proceder
        return
    
    is_preloading = True  # Marca el inicio de la ejecución

    current_dir = os.getcwd()

    # Construyes la ruta hacia la carpeta 'temp' dentro del directorio actual
    temp_dir = os.path.join(current_dir, 'temp')

    item_details = fetch_item_details(item_id, user_id, api_key)
    if item_details is None:
        return

    path = item_details['MediaSources'][0].get("Path", "")
    
    if ("download" in path or "direct" in path) \
        and "crunchyroll" in path:


        # Usamos un thread para cancelar la solicitud después de 5 segundos
        def download_and_cancel():
            with requests.get(path, stream=True) as r:
                time.sleep(5)  # Esperamos 5 segundos y luego cancelamos la solicitud
                #print("Preloading cancelled after 5 seconds")

        crunchyroll_id = path.split('_')[-1]

        isin = False
        # Iterar sobre todos los archivos en la carpeta 'temp'
        for filename in os.listdir(temp_dir):
            # Comprobar si el crunchroll_id está en el nombre del archivo
            if crunchyroll_id in filename:
                isin = True
                # Si necesitas hacer algo más que imprimir, este es el lugar.
                # Por ejemplo, podrías romper el bucle con 'break' si solo te interesa saber si al menos uno existe

        if not isin:
            preload_thread = threading.Thread(target=download_and_cancel)
            preload_thread.start()
            #print("Preloading started...")
    else:
        #print("The path does not contain the word 'download'.")
        pass 
    is_preloading = False  # Restablece el estado
    preload_lock.release()  # Libera el Lock

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
                        #print(f"El siguiente episodio ID es {siguiente_episodio_id}")
                        #print("precargando...")
                        preload_video(siguiente_episodio_id, user_id, api_key)
                        # Aquí puedes agregar la lógica para "precargar" el siguiente episodio
                    else:
                        pass
                        #print("No se encontró el siguiente episodio o ya estás en el último episodio.")
        else:
            print(f"Error: El servidor devolvió un estado HTTP {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"Error HTTP: {e}")
    except ValueError as e:
        print(f"Error JSON: {e}")

def daemon():
    #print(' * Running Crunchyroll Jellyfin daemon')
    """Inicia el daemon que verificará el estado de reproducción cada minuto."""
    if not base_url == "" \
    and not api_key == "" :
        schedule.every(1).minutes.do(preload_next_episode)

        while True:
            schedule.run_pending()
            time.sleep(1)
