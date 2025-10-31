from flask import send_file, redirect, stream_with_context, Response, abort
from sanitize_filename import sanitize
import os
import ffmpeg
import time
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
            self.last_episode_file = "{}/{}/{}.{}".format(
                media_folder, 
                sanitize(
                    "{}".format(
                        self.channel_folder
                    )
                ), 
                "last_episode", 
                "txt"
            )
            self.new_content = False
            self.last_episode = self.get_start_episode()
            self.videos = self.get_videos()
    
    def get_videos(self):
        # Autenticamos usando credenciales del config.json
        auth_command = [
            'node', 'D:\\opt\\multi-downloader-nx\\lib\\index.js',
            '--service', 'crunchy',
            '-u', crunchyroll_username,
            '-p', crunchyroll_password,
            '--auth'
        ]
        l.log("crunchyroll", "Authenticating with Crunchyroll...")
        l.log("crunchyroll", f"Auth command: node index.js --service crunchy -u {crunchyroll_username} -p *** --auth")
        result = subprocess.run(auth_command, capture_output=True, text=True, stdin=subprocess.DEVNULL)
        if result.returncode != 0:
            l.log("crunchyroll", f"Auth error: {result.stderr}")
        else:
            l.log("crunchyroll", "Authentication successful")

        # Extraemos el ID de la serie de la URL
        # Formato: https://www.crunchyroll.com/es/series/GY5P48XEY/demon-slayer-kimetsu-no-yaiba
        # Necesitamos el ID (GY5P48XEY), no el slug (demon-slayer-kimetsu-no-yaiba)
        url_parts = self.channel_url.split('/')
        if 'series' in url_parts:
            series_index = url_parts.index('series')
            series_id = url_parts[series_index + 1]  # El ID está después de 'series'
        else:
            series_id = url_parts[-1]  # Fallback al último elemento

        # Convertir locale a formato válido (ja-JP -> und para japonés, es-419 para español, etc)
        # Según la ayuda, los locales válidos son: en-US, es-419, pt-BR, fr-FR, de-DE, etc
        locale_map = {
            'ja-JP': 'und',  # Japonés
            'es-ES': 'es-ES',
            'es-419': 'es-419',
            'en-US': 'en-US',
            'pt-BR': 'pt-BR',
            'fr-FR': 'fr-FR',
            'de-DE': 'de-DE'
        }
        valid_locale = locale_map.get(subtitle_language, 'en-US')
        
        # Obtener lista de episodios
        command = [
            'node', 'D:\\opt\\multi-downloader-nx\\lib\\index.js',
            '--service', 'crunchy',
            '--series', series_id,
            '--locale', valid_locale
        ]
        
        l.log("crunchyroll", f"Getting episodes for series: {series_id}")
        l.log("crunchyroll", f"Command: {' '.join(command)}")
        self.set_proxy(command)
        
        # Ejecutar con stdin para enviar "0" (seleccionar todas las temporadas)
        process = subprocess.Popen(
            command, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            stdin=subprocess.PIPE,  # Permitir entrada
            text=True, 
            bufsize=1, 
            universal_newlines=True
        )
        
        # Leer salida hasta que aparezca el prompt de selección, luego enviar "0"
        import threading
        def send_selection():
            import time
            time.sleep(3)  # Esperar 3 segundos para que muestre el menú
            try:
                process.stdin.write("0\n")
                process.stdin.flush()
                l.log("crunchyroll", "Sent selection: 0")
            except Exception as e:
                l.log("crunchyroll", f"Error sending selection: {e}")
        
        # Enviar selección en un thread separado
        threading.Thread(target=send_selection, daemon=True).start()
        
        return process

    def get_start_episode(self):
        last_episode = 0
        if not os.path.isfile(self.last_episode_file):
            self.new_content = True
            f.folders().write_file(self.last_episode_file, "0")
        else:
            with open(self.last_episode_file) as fl:
                last_episode = fl.readlines()
                fl.close()
            
            last_episode = last_episode[0]
        
        return last_episode

    def set_start_episode(self, command):
        # multi-downloader-nx no usa --playlist-start, filtramos después
        pass

    def set_last_episode(self, playlist_count):
        if self.new_content:
            f.folders().write_file(
                self.last_episode_file, 
                playlist_count
            )
        else:
            #sum_episode = int(self.last_episode) + int(playlist_count)
            f.folders().write_file(
                self.last_episode_file,
                str(playlist_count)
            )

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
#if jellyfin_preload:
#    threading.Thread(target=daemon, daemon=False).start()
## -- END

## -- MANDATORY TO_STRM FUNCTION 
def to_strm(method):
    for crunchyroll_channel in channels:
        log_text = ("Preparing channel {}".format(crunchyroll_channel))
        l.log("crunchyroll", log_text)

        crunchyroll = Crunchyroll(crunchyroll_channel)
        #crunchyroll.get_cookie_from_firefox()

        # -- MAKES CHANNEL DIR (AND SUBDIRS) IF NOT EXIST, REMOVE ALL STRM IF KEEP_OLDER_STRM IS SETTED TO FALSE IN GENERAL CONFIG
        f.folders().make_clean_folder(
            "{}/{}".format(
                media_folder,  
                sanitize(
                    "{}".format(
                        crunchyroll.channel_folder
                    )
                )
            ),
            False,
            config
        )
        ## -- END

        # -- BUILD STRM
        process = crunchyroll.videos
        file_content = ""
        try:
            for line in iter(process.stdout.readline, ''):
                if line:
                    line_str = line.rstrip()
                    l.log("crunchyroll", f"Output: {line_str}")  # Debug
                    
                    if not line_str or 'ERROR' in line_str or 'WARNING' in line_str:
                        continue
                    
                    if '[S' in line_str and 'E' in line_str and '] - ' in line_str:
                        # Ejemplo: [S206E1] - El Pilar de las Llamas, Kyojuro Rengoku [✓ Japanese]
                        season_info = line_str[line_str.find('[')+1:line_str.find(']')]
                        episode_title = line_str[line_str.find('] - ')+4:line_str.rfind('[')].strip()
                        
                        season_number = season_info[1:4]  # 206
                        episode_number = season_info[5:].replace('E', '')  # 1
                        
                        # Crear la URL usando el formato de Crunchyroll
                        url = self.channel_url + '/episode-' + episode_number
                        
                        # Diccionario para almacenar los valores extraídos para comparación y posible reemplazo.
                        data = {
                            'season_number': season_number,
                            'season': episode_title,
                            'episode_number': episode_number.zfill(4),
                            'episode': episode_title,
                            'url': url.replace('https://www.crunchyroll.com/', '').replace('/', '_'),
                            'playlist_count': '1'
                        }

                    # Verifica si hay mutaciones especificadas para este canal.
                    if crunchyroll_channel in mutate_values:
                        for values in mutate_values[crunchyroll_channel]:
                            # Obtén el campo y el valor objetivo a mutar del diccionario 'values'.
                            field = values['field']
                            value = values['value']

                            # Si el valor actual en el campo corresponde al valor objetivo, reemplázalo.
                            if field in data and data[field] == value:
                                data[field] = values['replace']

                    # Actualiza las variables con los valores posiblemente mutados.
                    season_number, season, episode_number, episode, url, playlist_count = (
                        data['season_number'], data['season'], data['episode_number'], data['episode'], data['url'], data['playlist_count']
                    )
                                                        
                    if not episode_number == '0' and not episode_number  == 0:

                        video_name = "{} - {}".format(
                            "S{}E{}".format(
                                season_number, 
                                episode_number
                            ), 
                            episode
                        )

                        file_content = "http://{}:{}/{}/{}/{}".format(
                            ytdlp2strm_config['ytdlp2strm_host'], 
                            ytdlp2strm_config['ytdlp2strm_port'], 
                            source_platform, 
                            method, 
                            url
                        )

                        file_path = "{}/{}/{}/{}.{}".format(
                            media_folder,  
                            sanitize(
                                "{}".format(
                                    crunchyroll.channel_folder
                                )
                            ),  
                            sanitize(
                                "S{} - {}".format(
                                    season_number, 
                                    season
                                )
                            ), 
                            sanitize(video_name), 
                            "strm"
                        )

                        f.folders().make_clean_folder(
                            "{}/{}/{}".format(
                                media_folder,  
                                sanitize(
                                    "{}".format(
                                        crunchyroll.channel_folder
                                    )
                                ),  
                                sanitize(
                                    "S{} - {}".format(
                                        season_number, 
                                        season
                                    )
                                )
                            ),
                            False,
                            config
                        )

                        if not os.path.isfile(file_path):
                            f.folders().write_file(
                                file_path, 
                                file_content
                            )

                        if crunchyroll.new_content:
                            crunchyroll.set_last_episode(playlist_count)
                        else:
                            try:
                                sum_episode = int(crunchyroll.last_episode) + int(playlist_count)
                            except:
                                try:
                                    sum_episode = 1 + int(playlist_count)
                                except:
                                    sum_episode = 1

                            crunchyroll.set_last_episode(
                                str(sum_episode)
                            )

                if not line:
                    if jellyfin_preload_last_episode and (method == 'download' or method =='direct'):
                        if 'http' in file_content:
                            w.worker(file_content).preload()
                    break
            
            # Leer stderr para ver errores
            stderr_output = process.stderr.read()
            if stderr_output:
                l.log("crunchyroll", f"Stderr: {stderr_output}")
                
        finally:
            process.kill()
        ## -- END
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

def download(crunchyroll_id):
    current_dir = os.getcwd()
    temp_dir = os.path.join(current_dir, 'temp')
    
    # Extraer series ID y episode number del crunchyroll_id
    # Formato esperado: series_episode-X donde X es el número de episodio
    url_parts = crunchyroll_id.replace('_', '/')
    
    # Buscar archivo ya descargado
    existing_file = None
    for filename in os.listdir(temp_dir):
        if crunchyroll_id in filename and (filename.endswith('.mp4') or filename.endswith('.mkv')):
            existing_file = os.path.join(temp_dir, filename)
            break
    
    if not existing_file:
        l.log("crunchyroll", f"Downloading episode: {crunchyroll_id}")
        
        # Comando de descarga usando multi-downloader-nx
        command = [
            'node', 'D:\\opt\\multi-downloader-nx\\lib\\index.js',
            '--service', 'crunchy',
            '--url', f'https://www.crunchyroll.com/{url_parts}',
            '--tsd',  # Descargar temporadas completas
            '--locale', audio_language,
            '--syncTiming',  # Sincronizar subtítulos
            '--dlsubs', subtitle_language if subtitle_language else 'all',
            '--output', os.path.join(temp_dir, f'{crunchyroll_id}.mp4')
        ]
        
        Crunchyroll().set_proxy(command)
        
        # Ejecutar descarga
        process = subprocess.run(command, capture_output=True, text=True)
        
        if process.returncode != 0:
            l.log("crunchyroll", f"Error downloading: {process.stderr}")
            abort(500)
        
        # Buscar el archivo descargado
        for filename in os.listdir(temp_dir):
            if crunchyroll_id in filename and (filename.endswith('.mp4') or filename.endswith('.mkv')):
                existing_file = os.path.join(temp_dir, filename)
                break
        
        if not existing_file:
            l.log("crunchyroll", "Downloaded file not found")
            abort(404)
    
    l.log("crunchyroll", f"Serving file: {existing_file}")
    return send_file(existing_file)

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