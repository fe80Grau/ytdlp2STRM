from flask import send_file, redirect, stream_with_context, Response, abort
from utils.sanitize import sanitize
import os
import ffmpeg
import time
import json
from clases.config import config as c
from clases.worker import worker as w
from clases.folders import folders as f
from clases.nfo import nfo as n
from clases.log import log as l
from plugins.crunchyroll.jellyfin import daemon
import subprocess
import threading

## -- CRUNCHYROLL CLASS
class Crunchyroll:
    def __init__(self, channel=False):
        if channel:
            self.channel = channel.replace("https://www.crunchyroll.com/","")
            self.channel_url = "https://www.crunchyroll.com/{}".format(self.channel)
            self.channel_folder = self.channel.split('/')[-1]
            self.videos = self.get_videos()
    
    def authenticate(self):
        """Autenticar con Crunchyroll usando multi-downloader-nx"""
        auth_command = [
            'node', multi_downloader_path,
            '--service', 'crunchy',
            '--username', crunchyroll_username,
            '--password', crunchyroll_password,
            '--auth'
        ]
        l.log("crunchyroll", "Authenticating with Crunchyroll...")
        result = subprocess.run(auth_command, capture_output=True, text=True, stdin=subprocess.DEVNULL)
        if result.returncode != 0:
            l.log("crunchyroll", f"Auth error: {result.stderr}")
            return False
        l.log("crunchyroll", "Authentication successful")
        return True
    
    def get_series_id(self):
        """Extraer el ID de la serie de la URL"""
        # Formato: https://www.crunchyroll.com/es/series/GY5P48XEY/demon-slayer-kimetsu-no-yaiba
        url_parts = self.channel_url.split('/')
        if 'series' in url_parts:
            series_index = url_parts.index('series')
            series_id = url_parts[series_index + 1]
            #l.log("crunchyroll", f"Extracted series_id: {series_id} from URL: {self.channel_url}")
            return series_id
        
        # Si no tiene /series/, buscar un ID que empiece con G (formato Crunchyroll)
        for part in url_parts:
            if part and part.startswith('G') and len(part) > 5:
                l.log("crunchyroll", f"Extracted series_id: {part} from URL: {self.channel_url}")
                return part
        
        l.log("crunchyroll", f"WARNING: Could not extract series_id from URL: {self.channel_url}")
        return None
    
    def get_videos(self):
        """Obtener lista de episodios usando --series y parseando la salida"""
        import time
        
        l.log("crunchyroll", "Fetching episodes from Crunchyroll...")
        
        # Autenticar
        if not self.authenticate():
            return []
        
        series_id = self.get_series_id()
        
        # PASO 1: Listar solo las temporadas (rápido, <30s)
        command = [
            'node', multi_downloader_path,
            '--service', 'crunchy',
            '--series', series_id,
            '--locale', valid_locale
        ]
        
        self.set_proxy(command)
        l.log("crunchyroll", f"Getting seasons list for series: {series_id}")
        l.log("crunchyroll", f"Command: {' '.join(command)}")
        
        # Ejecutar y matar después de 30 segundos (solo necesitamos la lista de temporadas)
        import time
        import threading
        
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE,
            bufsize=0,
            encoding='utf-8',
            errors='replace'
        )
        
        # Enviar "0" para cancelar la selección
        time.sleep(2)
        try:
            process.stdin.write("0\n")
            process.stdin.flush()
            process.stdin.close()
        except:
            pass
        
        # Leer salida con timeout de 30 segundos
        output_lines = []
        error_lines = []
        
        def read_stream(stream, lines_list):
            try:
                for line in iter(stream.readline, ''):
                    if not line:
                        break
                    lines_list.append(line)
            except Exception as e:
                l.log("crunchyroll", f"Error reading stream: {e}")
        
        stdout_thread = threading.Thread(target=read_stream, args=(process.stdout, output_lines))
        stderr_thread = threading.Thread(target=read_stream, args=(process.stderr, error_lines))
        
        stdout_thread.start()
        stderr_thread.start()
        
        # Esperar máximo 30 segundos
        start_time = time.time()
        timeout = 30
        
        while process.poll() is None:
            elapsed = int(time.time() - start_time)
            if elapsed > timeout:
                l.log("crunchyroll", f"Stopping season list command after {timeout}s")
                process.kill()
                break
            time.sleep(0.5)
        
        stdout_thread.join(timeout=5)
        stderr_thread.join(timeout=5)
        
        output = ''.join(output_lines)
        l.log("crunchyroll", f"Seasons list received ({len(output)} chars)")
        
        # Parsear la salida para extraer season_id y episodios
        episodes = []
        current_season_id = None
        current_season_number = None
        current_season_name = None
        
        # Mapeo de season_id a información de temporada (para corregir nombres)
        seasons_map = {}
        
        # Primera pasada: extraer información de todas las temporadas
        for line in output.split('\n'):
            line = line.strip()
            if line.startswith('[S:') and ']' in line:
                try:
                    season_id = line[line.find('[S:')+3:line.find(']')]
                    # Extraer nombre de temporada (después de ] y antes de (Season:)
                    season_title = line[line.find(']')+1:].strip()
                    if '(Season:' in season_title:
                        season_title = season_title[:season_title.find('(Season:')].strip()
                    
                    # Extraer número de temporada
                    season_num = "1"
                    if '(Season:' in line:
                        season_num_str = line[line.find('(Season:')+8:line.find(')', line.find('(Season:'))]
                        season_num = season_num_str.strip()
                    
                    seasons_map[season_id] = {
                        'number': season_num,
                        'name': season_title
                    }
                    l.log("crunchyroll", f"Found season: {season_id} (S{season_num}) - {season_title[:50]}")
                except Exception as e:
                    l.log("crunchyroll", f"Error parsing season: {e}")
        
        l.log("crunchyroll", f"Found {len(seasons_map)} seasons, now fetching episodes for each...")
        
        # PASO 2: Para cada temporada, obtener sus episodios
        episodes = []
        specials_count = 0  # Contador global de especiales
        absolute_episode_number = 0  # Contador global de episodios (no especiales)
        season_episode_counts = {}  # Contador de episodios por season_number (para manejar temporadas duplicadas)
        
        for season_id, season_info in seasons_map.items():
            season_number = season_info['number']
            season_name = season_info['name']
            
            # Inicializar contador para este season_number si no existe
            if season_number not in season_episode_counts:
                season_episode_counts[season_number] = 0
            
            l.log("crunchyroll", f"Fetching episodes for season {season_id} (S{season_number})...")
            
            # Comando para obtener episodios de una temporada específica
            # Usar --series junto con -s para filtrar la temporada
            command = [
                'node', multi_downloader_path,
                '--service', 'crunchy',
                '--series', series_id,
                '-s', season_id,
                '--locale', valid_locale
            ]
            
            self.set_proxy(command)
            
            try:
                # Ejecutar comando con timeout de 60 segundos por temporada
                result = subprocess.run(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=60
                )
                
                season_output = result.stdout.decode('utf-8', errors='replace')
                
                # Log para debug (solo primeras 500 chars)
                if len(season_output) < 100:
                    l.log("crunchyroll", f"  Output: {season_output[:200]}")
                
                # Parsear episodios de esta temporada
                # Usar el contador del season_number (no resetear si hay múltiples season_id con mismo número)
                episode_count_before = season_episode_counts[season_number]
                for line in season_output.split('\n'):
                    line = line.strip()
                    
                    # Detectar episodios normales [E1] o especiales [S1]
                    # IMPORTANTE: [S:XXX] son temporadas, NO especiales
                    # Los especiales son [S1], [S2], etc. (sin dos puntos)
                    is_special = line.startswith('[S') and not line.startswith('[S:')
                    is_episode = line.startswith('[E')
                    
                    if (is_episode or is_special) and ']' in line:
                        try:
                            # Extraer número de episodio: [E1] o [S1]
                            prefix = '[S' if is_special else '[E'
                            ep_num = line[line.find(prefix)+2:line.find(']')]
                            
                            # Extraer título (después de la segunda ])
                            # Formato: [E1] [2021-10-10] Título - Season 206 - Título Episodio
                            rest_of_line = line[line.find(']')+1:]  # Después de [E1] o [S1]
                            if ']' in rest_of_line:
                                rest_of_line = rest_of_line[rest_of_line.find(']')+1:].strip()  # Después de [fecha]
                            
                            # Extraer el título del episodio
                            episode_title = rest_of_line.strip()
                            
                            # Si hay " - Season XXX - ", el título real está después
                            if ' - Season' in rest_of_line:
                                # Buscar el último " - Season" en la línea
                                season_start = rest_of_line.rfind(' - Season')
                                after_season = rest_of_line[season_start:]  # Desde " - Season"
                                
                                # Buscar el siguiente " - " después de "Season XXX"
                                parts = after_season.split(' - ', 2)  # Dividir en máximo 3 partes
                                if len(parts) >= 3:
                                    # parts[0] = "", parts[1] = "Season 14", parts[2] = "Título"
                                    episode_title = parts[2].strip()
                                elif len(parts) == 2:
                                    # Solo hay "Season 14" sin título después
                                    episode_title = rest_of_line[:season_start].strip()
                            
                            if is_special:
                                # Es un especial - va a carpeta Specials
                                specials_count += 1
                                episodes.append({
                                    'season_id': 'specials',
                                    'season_number': '00',  # Temporada 00 para especiales
                                    'episode_id': f"S{ep_num}",  # Mantener el ID original del especial
                                    'episode_number': f"S{ep_num}",
                                    'season_episode_number': specials_count,  # Número incremental de especiales
                                    'title': episode_title,
                                    'season_name': 'Specials',
                                    'description': ''
                                })
                            else:
                                # Episodio normal - usar contador absoluto
                                season_episode_counts[season_number] += 1
                                absolute_episode_number += 1
                                
                                current_season_ep = season_episode_counts[season_number]
                                
                                episodes.append({
                                    'season_id': season_id,
                                    'season_number': season_number,
                                    'episode_id': str(absolute_episode_number),  # Número absoluto global
                                    'episode_number': str(absolute_episode_number),
                                    'season_episode_number': current_season_ep,  # Número dentro de esta temporada (continúa si hay duplicados)
                                    'title': episode_title,
                                    'season_name': season_name,
                                    'description': ''
                                })
                            
                        except Exception as e:
                            l.log("crunchyroll", f"Error parsing episode: {e} | Line: {line[:80]}")
                
                episodes_added = season_episode_counts[season_number] - episode_count_before
                l.log("crunchyroll", f"  -> Found {episodes_added} episodes for season {season_id} (S{season_number} now has {season_episode_counts[season_number]} total episodes)")
                
            except subprocess.TimeoutExpired:
                l.log("crunchyroll", f"Timeout fetching episodes for season {season_id}")
            except Exception as e:
                l.log("crunchyroll", f"Error fetching season {season_id}: {e}")
        
        l.log("crunchyroll", f"Found {len(episodes)} episodes total")
        return episodes

    def set_auth(self, command, quotes=False):
        # La autenticación es manejada por multi-downloader-nx
        pass

    def set_proxy(self, command):
        if proxy:
            if proxy_url != "":
                command.append('--proxy')
                command.append(proxy_url)

## -- END

## -- LOAD CONFIG AND CHANNELS FILES
ytdlp2strm_config = c.config(
    './config/config.json'
).get_config()

config = c.config(
    './plugins/crunchyroll/config.json'
).get_config()

channels = c.config(
    config["channels_list_file"]
).get_channels()

mutate_values = c.config(
    config["mutate_values"]
).get_channels()

source_platform = "crunchyroll"
media_folder = config["strm_output_folder"]
channels_list = config["channels_list_file"]
subtitle_language = config["crunchyroll_subtitle_language"]
audio_language = config['crunchyroll_audio_language']
crunchyroll_username = config.get('crunchyroll_username', '')
crunchyroll_password = config.get('crunchyroll_password', '')

# Multi-downloader-nx configuration
multi_downloader_path = config.get('multi_downloader_path', 'D:\\opt\\multi-downloader-nx\\lib\\index.js')

# Mapeo de locales
locale_map = {
    'ja-JP': 'und',
    'es-ES': 'es-ES',
    'es-419': 'es-419',
    'en-US': 'en-US',
    'pt-BR': 'pt-BR',
    'fr-FR': 'fr-FR',
    'de-DE': 'de-DE'
}
valid_locale = locale_map.get(subtitle_language, 'en-US')
jellyfin_preload = False
jellyfin_preload_last_episode = False
port = ytdlp2strm_config['ytdlp2strm_port']
SECRET_KEY = os.environ.get('AM_I_IN_A_DOCKER_CONTAINER', False)
DOCKER_PORT = os.environ.get('DOCKER_PORT', False)
if SECRET_KEY:
    port = DOCKER_PORT


if 'jellyfin_preload' in config:
    jellyfin_preload = bool(config['jellyfin_preload'])
if 'jellyfin_preload_last_episode' in config:
    jellyfin_preload_last_episode = bool(config['jellyfin_preload_last_episode'])
if 'proxy' in config:
    proxy = config['proxy']
    proxy_url = config['proxy_url']
else:
    proxy = False
    proxy_url = ""
## -- END

## -- JELLYFIN DAEMON
if jellyfin_preload:
    threading.Thread(target=daemon, daemon=True).start()
## -- END

## -- MANDATORY TO_STRM FUNCTION 
def to_strm(method):
    for crunchyroll_channel in channels:
        l.log("crunchyroll", f"Preparing channel {crunchyroll_channel}")

        crunchyroll = Crunchyroll(crunchyroll_channel)

        # Crear carpeta principal de la serie
        series_folder = "{}/{}".format(
            media_folder,  
            sanitize(crunchyroll.channel_folder)
        )
        
        f.folders().make_clean_folder(series_folder, False, config)

        # Obtener lista de episodios
        episodes = crunchyroll.videos
        
        if not episodes or len(episodes) == 0:
            l.log("crunchyroll", "No episodes found")
            continue
        
        l.log("crunchyroll", f"Found {len(episodes)} episodes")
        
        # Obtener series ID de la URL
        series_id = crunchyroll.get_series_id()
        l.log("crunchyroll", f"Using series_id: {series_id} for all episodes")
        
        # Agrupar episodios por season_number y crear nombres unificados sin paréntesis
        import re
        unified_season_names = {}
        for ep in episodes:
            season_num = str(ep['season_number']).zfill(2)
            if season_num not in unified_season_names:
                season_name = ep.get('season_name', f'Season {season_num}')
                # Quitar paréntesis y su contenido: (1089-1122), (Season: 14), etc.
                clean_name = re.sub(r'\s*\([^)]*\)\s*', ' ', season_name)
                # Limpiar espacios múltiples
                clean_name = re.sub(r'\s+', ' ', clean_name).strip()
                unified_season_names[season_num] = clean_name
        
        # Procesar cada episodio
        total_episodes = len(episodes)
        for idx, ep in enumerate(episodes, 1):
            season_number = str(ep['season_number']).zfill(2)  # S01, S02, etc.
            episode_number = str(ep['season_episode_number']).zfill(2)  # Número dentro de la temporada
            episode_title = ep['title']
            episode_id = ep['episode_id']  # Número absoluto de Crunchyroll (E37)
            season_id = ep['season_id']
            # Usar el nombre unificado sin paréntesis
            season_name = unified_season_names.get(season_number, ep.get('season_name', episode_title))
            
            # Diccionario para mutaciones
            data = {
                'season_number': season_number,
                'season': season_name,
                'episode_number': episode_number,
                'episode': episode_title,
                'url': f"{series_id}_{episode_id}",  # Usar series_id y episode_id global
                'playlist_count': '1'
            }
            
            # Aplicar mutaciones si existen
            if crunchyroll_channel in mutate_values:
                for values in mutate_values[crunchyroll_channel]:
                    field = values['field']
                    value = values['value']
                    if field in data and data[field] == value:
                        data[field] = values['replace']
            
            # Actualizar variables con valores mutados
            season_number = data['season_number']
            episode_number = data['episode_number']
            episode_title = data['episode']
            season_name = data['season']
            url = data['url']
            
            # Crear nombre del archivo con título del episodio
            video_name = f"S{season_number}E{episode_number} - {episode_title}"
            
            # Crear contenido del STRM
            file_content = "http://{}:{}/{}/{}/{}".format(
                ytdlp2strm_config['ytdlp2strm_host'], 
                ytdlp2strm_config['ytdlp2strm_port'], 
                source_platform, 
                method, 
                url
            )
            
            # Crear carpeta de temporada con el nombre de la temporada
            season_folder = "{}/{}/S{} - {}".format(
                media_folder,
                sanitize(crunchyroll.channel_folder),
                season_number,
                sanitize(season_name)
            )
            
            f.folders().make_clean_folder(season_folder, False, config)
            
            # Crear archivo STRM
            file_path = "{}/{}.strm".format(
                season_folder,
                sanitize(video_name)
            )
            
            if not os.path.isfile(file_path):
                f.folders().write_file(file_path, file_content)
                # Solo hacer log cada 50 episodios, el primero y el último para no saturar
                if idx == 1 or idx == total_episodes or idx % 50 == 0:
                    l.log("crunchyroll", f"Created: {video_name} ({idx}/{total_episodes})")
        
        # Si jellyfin_preload_last_episode está activado, descargar el último episodio
        if jellyfin_preload_last_episode and len(episodes) > 0:
            last_episode = episodes[-1]
            last_episode_id = last_episode['episode_id']
            last_episode_title = last_episode['title']
            crunchyroll_id = f"{series_id}_{last_episode_id}"
            
            l.log("crunchyroll", f"Preloading last episode: {last_episode_title} (ID: {crunchyroll_id})")
            
            # Ejecutar descarga en un thread separado para no bloquear
            def preload_last_episode_func():
                try:
                    result = download(crunchyroll_id, return_file=False)
                    if result:
                        l.log("crunchyroll", f"Successfully preloaded: {last_episode_title}")
                    else:
                        l.log("crunchyroll", f"Failed to preload: {last_episode_title}")
                except Exception as e:
                    l.log("crunchyroll", f"Error preloading last episode: {e}")
            
            threading.Thread(target=preload_last_episode_func, daemon=True).start()
        
        l.log("crunchyroll", f"Finished processing {crunchyroll_channel}")
    
    return True 
## -- END

## -- EXTRACT / REDIRECT VIDEO DATA 

def direct(crunchyroll_id): 
    '''
    command = [
        'D:\\opt\\multi-downloader-nx-cli\\aniDL.exe',
        '--service', 'crunchy',
        '--url', 'https://www.crunchyroll.com/{}'.format(crunchyroll_id.replace('_','/')),
        '--quality', 'best',
        '--locale', f'{audio_language}',
        '--get-url'
    ]
    Crunchyroll().set_proxy(command)
    crunchyroll_url = w.worker(command).output()
    return redirect(crunchyroll_url, code=301)
    '''

    return download(crunchyroll_id)

def download(crunchyroll_id, return_file=True):
    current_dir = os.getcwd()
    temp_dir = os.path.join(current_dir, 'temp')
    
    # Extraer series_id y episode_id del crunchyroll_id
    # Formato: series_id_episode_id
    try:
        series_id, episode_id = crunchyroll_id.split('_', 1)
    except:
        l.log("crunchyroll", f"Invalid crunchyroll_id format: {crunchyroll_id}")
        if return_file:
            abort(400)
        return None
    
    # Buscar archivo ya descargado
    existing_file = None
    valid_extensions = ('.mp4', '.mkv', '.ts', '.avi', '.mov')
    for filename in os.listdir(temp_dir):
        if crunchyroll_id in filename and filename.lower().endswith(valid_extensions):
            existing_file = os.path.join(temp_dir, filename)
            break
    
    if not existing_file:
        l.log("crunchyroll", f"Downloading episode: {episode_id} from series: {series_id}")
        
        # Mapeo de dubLang
        dub_map = {
            'ja-JP': 'jpn',
            'es-ES': 'spa-ES',
            'es-419': 'spa-419',
            'en-US': 'eng',
            'pt-BR': 'por',
            'fr-FR': 'fra',
            'de-DE': 'deu'
        }
        dub_lang = dub_map.get(audio_language, 'jpn')
        
        # Comando de descarga usando multi-downloader-nx
        # Usar ruta absoluta en fileName para forzar descarga en temp_dir
        output_path = os.path.join(temp_dir, crunchyroll_id)
        
        command = [
            'node', multi_downloader_path,
            '--service', 'crunchy',
            '--series', series_id,  # Usar --series con series ID
            '--dubLang', dub_lang,
            '--dlsubs', subtitle_language if subtitle_language else 'all',
            '--locale', valid_locale,
            '--tsd',
            '-q', '0',  # Máxima calidad
            '-e', episode_id,
            '--fileName', output_path  # Ruta absoluta
        ]
        
        Crunchyroll().set_proxy(command)
        
        # Asegurar que existe la carpeta logs para multi-downloader-nx
        multi_downloader_dir = os.path.dirname(multi_downloader_path)
        logs_dir = os.path.join(multi_downloader_dir, 'logs')
        os.makedirs(logs_dir, exist_ok=True)
        
        # Ejecutar descarga con stdin para seleccionar episodio
        l.log("crunchyroll", f"Command: {' '.join(command)}")
        
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE,
            text=True,
            cwd=temp_dir
        )
        
        
        # Esperar a que termine
        stdout, stderr = process.communicate(timeout=300)
        
        # Loguear la salida completa
        l.log("crunchyroll", "=== multi-downloader-nx ===")
        #if stdout:
        #    for line in stdout.split('\n'):
        #        if line.strip():
        #            l.log("crunchyroll", f"STDOUT: {line}")
        if stderr:
            for line in stderr.split('\n'):
                if line.strip():
                    l.log("crunchyroll", f"STDERR: {line}")
        l.log("crunchyroll", f"=== Return code: {process.returncode} ===")
        
        if process.returncode != 0:
            l.log("crunchyroll", f"Download failed with return code: {process.returncode}")
            if return_file:
                abort(500)
            return None
        
        # Buscar el archivo descargado (más extensiones y logging de debug)
        temp_files = os.listdir(temp_dir)
        l.log("crunchyroll", f"Files in temp: {temp_files}")
        for filename in temp_files:
            if crunchyroll_id in filename and filename.lower().endswith(valid_extensions):
                existing_file = os.path.join(temp_dir, filename)
                l.log("crunchyroll", f"Found downloaded file: {filename}")
                break
        
        if not existing_file:
            l.log("crunchyroll", f"Downloaded file not found (looked for {crunchyroll_id} with extensions {valid_extensions})")
            if return_file:
                abort(404)
            return None
    
    if return_file:
        l.log("crunchyroll", f"Serving file: {existing_file}")
        return send_file(existing_file)
    else:
        l.log("crunchyroll", f"File ready: {existing_file}")
        return existing_file

#experimental not works.
def streams(media, crunchyroll_id):
    log_text = (f'Remuxing {media} - {crunchyroll_id}')
    l.log("crunchyroll", log_text)
    command = None
    mimetype = None
    if media == 'audio':
        mimetype = 'audio/mp4'
        command = [
            'node', 'D:\\opt\\multi-downloader-nx\\lib\\index.js',
            '--service', 'crunchy',
            '--url', 'https://www.crunchyroll.com/{}'.format(crunchyroll_id.replace('_','/')),
            '--quality', 'best',
            '--locale', f'{audio_language}',
            '--format', 'bestaudio',
            '-o-'
        ]

    if media == 'video':
        mimetype = 'video/mp4'
        command = [
            'node', 'D:\\opt\\multi-downloader-nx\\lib\\index.js',
            '--service', 'crunchy',
            '--url', 'https://www.crunchyroll.com/{}'.format(crunchyroll_id.replace('_','/')),
            '--quality', 'best',
            '--locale', f'{audio_language}',
            '--format', 'bestvideo',
            '-o-'
        ]

    if command and mimetype:
        # Ejecutar el comando y obtener el output en modo binario
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        def generate():
            # Leer la salida en modo binario en pequeños bloques
            while True:
                output = process.stdout.read(1024)
                if output:
                    yield output
                else:
                    break

        def log_stderr():
            for line in iter(process.stderr.readline, b''):
                log_text (line.decode('utf-8', errors='ignore'))  # Imprimir la salida de error por consola
                l.log("crunchyroll", log_text)

        # Lanzar la función log_stderr en un hilo separado para capturar stderr mientras se transmite stdout
        threading.Thread(target=log_stderr).start()

        return Response(generate(), mimetype=mimetype)

    else:
        log_text = ('Please use a correct media type audio or video')
        l.log("crunchyroll", log_text)
        abort(500)

def remux_streams(crunchyroll_id):
    cleanup_frag_files()
    audio_url = f'http://localhost:{port}/crunchyroll/stream/audio/{crunchyroll_id}'
    video_url = f'http://localhost:{port}/crunchyroll/stream/video/{crunchyroll_id}'

    ffmpeg_command = [
        'ffmpeg',
        '-re',  # Read input at native frame rate
        '-protocol_whitelist', 'file,http,https,tcp,tls',
        '-i', video_url,  # Video input from URL
        '-re',  # Read input at native frame rate
        '-i', audio_url,  # Audio input from URL
        '-c', 'copy',  # Copy both audio and video without re-encoding
        '-f', 'matroska',  # Output format suitable for streaming
        'pipe:1'  # Output to stdout
    ]
    # Include robust FFmpeg input handling options
    ffmpeg_options = '-reconnect 1 -reconnect_at_eof 1 -reconnect_streamed 1 -reconnect_delay_max 2'.split()

    ffmpeg_command = ffmpeg_command[:1] + ffmpeg_options + ffmpeg_command[1:]
    ffmpeg_process = subprocess.Popen(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=10**8)

    # Event to signal that ffmpeg_process has finished
    ffmpeg_done_event = threading.Event()

    # Function to log stderr output
    def log_stderr():
        try:
            for line in iter(ffmpeg_process.stderr.readline, b''):
                log_text = (line.decode('utf-8', errors='ignore'))  # Log FFmpeg stderr output
                l.log("crunchyroll", log_text)

        except ValueError:
            pass  # Handle closed file stream silently
        finally:
            ffmpeg_done_event.set()  # Signal that stderr logging is done

    # Start the log_stderr function in a separate thread
    threading.Thread(target=log_stderr).start()

    def generate_ffmpeg_output():
        try:
            while True:
                output = ffmpeg_process.stdout.read(1024)
                if output:
                    yield output
                else:
                    break
        finally:
            # Ensure FFmpeg process is terminated
            log_text = ("Cleaning up FFmpeg process")
            l.log("crunchyroll", log_text)
            ffmpeg_process.terminate()
            ffmpeg_process.stdout.close()
            ffmpeg_process.stderr.close()
            # Wait for logging thread to finish
            ffmpeg_done_event.wait()
            # Clean up the --FragXX files
            cleanup_frag_files()
            
    headers = {
        'Content-Type': 'video/x-matroska',
        'Cache-Control': 'no-cache',
        'Content-Disposition': 'inline; filename="stream.mkv"'
    }
    return Response(stream_with_context(generate_ffmpeg_output()), mimetype='video/x-matroska', headers=headers)

def cleanup_frag_files():
    current_directory = os.getcwd()
    for file_name in os.listdir(current_directory):
        if file_name.startswith('--Frag'):
            file_path = os.path.join(current_directory, file_name)
            try:
                os.remove(file_path)
                log_text = (f'Removed fragment file: {file_path}')
                l.log("crunchyroll", log_text)
            except Exception as e:
                log_text = (f'Unable to remove fragment file: {file_path}. Error: {e}')
                l.log("crunchyroll", log_text)

## -- END