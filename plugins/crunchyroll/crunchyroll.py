from flask import stream_with_context, Response
from sanitize_filename import sanitize
import os
import glob
from clases.config import config as c
from clases.worker import worker as w
from clases.folders import folders as f
from clases.nfo import nfo as n
from datetime import datetime
import time
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
        print(' '.join(command))
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

source_platform = "crunchyroll"
media_folder = config["strm_output_folder"]
channels_list = config["channels_list_file"]
cookies_file = config["crunchyroll_cookies_file"]
subtitle_language = config["crunchyroll_subtitle_language"]
audio_language = config['crunchyroll_audio_language']
if 'proxy' in config:
    proxy = config['proxy']
    proxy_url = config['proxy_url']
else:
    proxy = False
    proxy_url = ""
## -- END

## -- MANDATORY TO_STRM FUNCTION 
def to_strm(method):
    for crunchyroll_channel in channels:
        print("Preparing channel {}".format(crunchyroll_channel))

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

        try:
            for line in iter(process.stdout.readline, b''):
                if line != "" and not 'ERROR' in line and not 'WARNING' in line:
                    #print(line)
                    season_number = str(line).rstrip().split(';')[0].zfill(2)
                    season = str(line).rstrip().split(';')[1]
                    episode_number = (line).rstrip().split(';')[2].zfill(4)
                    episode = (line).rstrip().split(';')[3]
                    url = (line).rstrip().split(';')[4].replace(
                        'https://www.crunchyroll.com/',
                        ''
                    ).replace('/','_')
                    playlist_count = (line).rstrip().split(';')[5]
               
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
                            #print(int(playlist_count))
                            try:
                                sum_episode = int(crunchyroll.last_episode) + int(playlist_count)
                            except:
                                try:
                                    sum_episode = 1 + int(playlist_count)
                                except:
                                    sum_episode = 1
                            #print(int(crunchyroll.last_episode))
                            #print(sum_episode)
                            crunchyroll.set_last_episode(
                                str(sum_episode)
                            )

                if not line: break
                
        finally:
            process.kill()
        ## -- END
    return True 
## -- END

## -- EXTRACT / REDIRECT VIDEO DATA 

def download_stream(crunchyroll_id, format_code, filename):
    command = [
        'yt-dlp', 
        '--no-warnings',
        '--format', '"{}"'.format(format_code), # Selecciona el mejor vídeo y el mejor audio
        '--match-filter', '"language={}"'.format(audio_language),
        '--extractor-args', '"crunchyrollbeta:hardsub={}"'.format(subtitle_language),
        '-o', f'{filename}',  # Especifica el nombre de archivo aquí
        'https://www.crunchyroll.com/{}'.format(crunchyroll_id.replace('_','/')),
    ]

    if format_code == '':
        command.pop(2)
        command.pop(2)
    Crunchyroll().set_auth(command,True)
    Crunchyroll().set_proxy(command)
    #print(' '.join(command))
    w.worker(command).output()

def direct(crunchyroll_id): 
    base_filename  = f"crunchyroll-{crunchyroll_id}"
    filepath_video_pattern = f"{base_filename}*.mp4.part"
    filepath_audio_pattern = f"{base_filename}*.m4a.part"

    # Video
    threading.Thread(target=download_stream, args=(crunchyroll_id, '', '{}{}'.format(base_filename, '.mp4'), )).start()

    # Audio
    threading.Thread(target=download_stream, args=(crunchyroll_id, 'ba*', '{}{}'.format(base_filename, '.m4a'), )).start()
    
    # La función generadora ahora lee el archivo de salida mientras se está descargando
    def generate():
        filepath_video = None
        filepath_audio = None

        # Espera hasta que el archivo aparezca
        while filepath_video is None:
            print(filepath_video_pattern)
            matching_files = glob.glob(filepath_video_pattern)
            if matching_files:
                filepath_video = matching_files[0]  # Tomamos el primer archivo que coincida
            else:
                time.sleep(1)

        while filepath_audio is None:
            print(filepath_audio_pattern)
            matching_files = glob.glob(filepath_audio_pattern)
            if matching_files:
                filepath_audio = matching_files[0]  # Tomamos el primer archivo que coincida
            else:
                time.sleep(1)

        time.sleep(3)
        def obtener_duracion(path_del_video):
            """
            Obtiene la duración de un video usando ffprobe.

            :param path_del_video: La ruta al archivo de video del cual obtener la duración.
            :return: duración del video en segundos.
            """
            comando = [
                'ffprobe',
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                path_del_video
            ]
            resultado = subprocess.run(comando, stdout=subprocess.PIPE, text=True)
            duracion = resultado.stdout.strip()
            return duracion

        def ffmpeg_stream():
            ffmpeg_command = [
                'ffmpeg',
                '-i', filepath_video,
                '-i', filepath_audio,
                '-c:v', 'copy',  # Especifica codec H264 para video
                '-c:a', 'copy',  # Copia el audio sin re-codificar
                '-strict', 'experimental',  # Puede ser necesario para algunos formatos de audio en MP4
                '-f', 'mp4',
                '-movflags', 'frag_keyframe+empty_moov',  # Permite la creación de MP4 fragmentado para streaming
                'pipe:1'
            ]
            process = subprocess.Popen(ffmpeg_command, stdout=subprocess.PIPE, bufsize=10**8)

            while True:
                data = process.stdout.read(1024)
                if not data:
                    break
                yield data

        video_duration = obtener_duracion(filepath_video)
        response = Response(stream_with_context(ffmpeg_stream()), content_type='video/mp4')
        response.headers['X-Video-Duration'] = video_duration  # Se añade la duración en un header personalizado.
        return response

    return generate()
    
## -- END