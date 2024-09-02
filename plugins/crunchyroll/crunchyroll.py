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
        command = [
            'yt-dlp', 
            '--print', '%(season_number)s;%(season)s;%(episode_number)s;%(episode)s;%(webpage_url)s;%(playlist_autonumber)s', 
            '--no-download',
            '--no-warnings',
            '--match-filter', 'language={}'.format(audio_language),
            '--extractor-args', 'crunchyrollbeta:hardsub={}'.format(subtitle_language),
            '{}'.format(self.channel_url),
            '--replace-in-metadata', '"season,episode"', '"[;/]"', '"-"'
        ]
        
        self.set_auth(command)
        self.set_proxy(command)
        self.set_start_episode(command)
        return w.worker(command).pipe() 

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
        if not self.new_content:
            try:
                next_episode = int(self.last_episode)
            except:
                next_episode = 1
            if next_episode < 1:
                next_episode = 1
            command.append('--playlist-start')
            command.append('{}'.format(next_episode))

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
        if config['crunchyroll_auth'] == "browser":
            command.append('--cookies-from-browser')
            if quotes:
                command.append(
                    '"{}"'.format(
                        config['crunchyroll_browser']
                    )
                )
            else:
                command.append(config['crunchyroll_browser'])

        if config['crunchyroll_auth'] == "cookies":
            command.append('--cookies')
            command.append(config['crunchyroll_cookies_file'])

        if config['crunchyroll_auth'] == "login":
            command.append('--username')
            command.append(config['crunchyroll_username'])
            command.append('--password')
            command.append(config['crunchyroll_password'])

        command.append('--user-agent')
        if quotes:
            command.append(
                '"{}"'.format(
                    config['crunchyroll_useragent']
                )
            )
        else:
            command.append(
                '{}'.format(
                    config['crunchyroll_useragent']
                )
            )

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
cookies_file = config["crunchyroll_cookies_file"]
subtitle_language = config["crunchyroll_subtitle_language"]
audio_language = config['crunchyroll_audio_language']
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
            for line in iter(process.stdout.readline, b''):
                if line != "" and not 'ERROR' in line and not 'WARNING' in line:
                    # Extrae los valores dividiendo la línea una sola vez y procesa según sea necesario.
                    split_line = str(line).rstrip().split(';')
                    season_number = split_line[0].zfill(2)
                    season = split_line[1]
                    episode_number = split_line[2].zfill(4)
                    episode = split_line[3]
                    url = split_line[4].replace('https://www.crunchyroll.com/', '').replace('/', '_')
                    playlist_count = split_line[5]

                    # Diccionario para almacenar los valores extraídos para comparación y posible reemplazo.
                    data = {
                        'season_number': season_number,
                        'season': season,
                        'episode_number': episode_number,
                        'episode': episode,
                        'url': url,
                        'playlist_count': playlist_count,
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
                
        finally:
            process.kill()
        ## -- END
    return True 
## -- END

## -- EXTRACT / REDIRECT VIDEO DATA 

def direct(crunchyroll_id): 
    '''
    command = [
        'yt-dlp', 
        '-f', 'best',
        '--no-warnings',
        '--match-filter', '"language={}"'.format(audio_language),
        '--extractor-args', '"crunchyrollbeta:hardsub={}"'.format(subtitle_language),
        'https://www.crunchyroll.com/{}'.format(crunchyroll_id.replace('_','/')),
        '--get-url'
    ]
    Crunchyroll().set_auth(command,True)
    Crunchyroll().set_proxy(command)
    crunchyroll_url = w.worker(command).output()
    return redirect(crunchyroll_url, code=301)
    '''

    return download(crunchyroll_id)

def download(crunchyroll_id):

    current_dir = os.getcwd()

    # Construyes la ruta hacia la carpeta 'temp' dentro del directorio actual
    temp_dir = os.path.join(current_dir, 'temp')

    def extract_media(command):
        subprocess.run(command)

    def preprocess_video(input_video, input_audio, output_file):
        """Pre-procesa el video y el audio para optimizarlo para streaming usando ffmpeg-python."""
        # Construir el gráfico de procesamiento de flujo para la entrada de video
        video_stream = ffmpeg.input(input_video)
        # Construir el gráfico de procesamiento de flujo para la entrada de audio
        audio_stream = ffmpeg.input(input_audio)
        
        # Combinar los flujos de video y audio, copiarlos sin recodificación y optimizarlos para el inicio rápido
        ffmpeg.output(
            video_stream, 
            audio_stream, 
            output_file, 
            c='copy', 
            movflags='faststart'
        ).run(overwrite_output=True)
    isin = False
    
    for filename in os.listdir(temp_dir):
        if crunchyroll_id in filename:
            isin = True

    if not isin:        
        command_video = [
            'yt-dlp', 
            '-f', 'bestvideo',
            '--no-warnings',
            '--no-mtime',
            '--extractor-args', 'crunchyrollbeta:hardsub={}'.format(subtitle_language),
            'https://www.crunchyroll.com/{}'.format(crunchyroll_id.replace('_','/')),
            '--output', os.path.join(temp_dir, f'{crunchyroll_id}.mp4')
        ]
        Crunchyroll().set_auth(command_video,False)
        Crunchyroll().set_proxy(command_video)

        command_audio = [
            'yt-dlp', 
            '-f', 'bestaudio',
            '--no-warnings',
            '--no-mtime',
            '--match-filter', 'language={}'.format(audio_language),
            '--extractor-args', 'crunchyrollbeta:hardsub={}'.format(subtitle_language),
            'https://www.crunchyroll.com/{}'.format(crunchyroll_id.replace('_','/')),
            '--output', os.path.join(temp_dir, f'{crunchyroll_id}.m4a')
        ]
        Crunchyroll().set_auth(command_audio,False)
        Crunchyroll().set_proxy(command_audio)

        video = threading.Thread(target=extract_media, args=(command_video,))
        audio = threading.Thread(target=extract_media, args=(command_audio,))

        video.start()
        audio.start()

        video.join()
        audio.join()
        
        preprocess_video(
            os.path.join(temp_dir, f'{crunchyroll_id}.mp4'), 
            os.path.join(temp_dir, f'{crunchyroll_id}.m4a'), 
            os.path.join(temp_dir, f'crunchyroll-{crunchyroll_id}.mp4')
        )

        
        f.folders().clean_waste(
            [
                os.path.join(temp_dir, f'{crunchyroll_id}.mp4'), 
                os.path.join(temp_dir, f'{crunchyroll_id}.m4a')
            ]
        )


    if isin and not os.path.isfile(os.path.join(temp_dir, f'crunchyroll-{crunchyroll_id}.mp4')):
        while not os.path.isfile(os.path.join(temp_dir, f'crunchyroll-{crunchyroll_id}.mp4')):
            time.sleep(5)
        isin = False
        
    return send_file(
        os.path.join(temp_dir, f'crunchyroll-{crunchyroll_id}.mp4')
    )
    #return stream_video(f'{crunchyroll_id}.mp4', f'{crunchyroll_id}.m4a')

#experimental not works.
def streams(media, crunchyroll_id):
    log_text = (f'Remuxing {media} - {crunchyroll_id}')
    l.log("crunchyroll", log_text)
    command = None
    mimetype = None
    if media == 'audio':
        mimetype = 'audio/mp4'
        command = [
            'yt-dlp', 
            '-f', 'bestaudio[ext=m4a]/bestaudio',
            '--no-warnings',
            '--no-part',
            '--no-mtime',
            '--match-filter', 'language={}'.format(audio_language),
            'https://www.crunchyroll.com/{}'.format(crunchyroll_id.replace('_','/')),
            '-o-'
        ]

    if media == 'video':
        mimetype = 'video/mp4'
        command = [
            'yt-dlp', 
            '-f', 'bestvideo',
            '--no-warnings',
            '--no-part',
            '--no-mtime',
            '--extractor-args', 'crunchyrollbeta:hardsub={}'.format(subtitle_language),
            'https://www.crunchyroll.com/{}'.format(crunchyroll_id.replace('_','/')),
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