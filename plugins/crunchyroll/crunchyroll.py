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

from clases.log import log as l

class Crunchyroll:
    def __init__(self, channel=False):
        self.channel = channel
        self.channel_id = channel.split('/')[-2]
        self.channel_folder = channel.split('/')[-1]
        self.new_content = False
        self.videos = self.get_videos()

    def get_videos(self):
        command = [
            "D:/opt/multi-downloader-nx-cli/aniDL.exe",
            "--service", "crunchy",
            "--series", self.channel_id
        ]

        lines = w.worker(command).shell().split('\n')
        videos = []
        for line in lines:
            if line.startswith('[') and not line.startswith('[Z'):
                data = line.split(' - ')
                episode_number = data[0].split(' ')[0].replace('[','').replace(']','').replace('E','')
                season_name = data[0].split('] ')[1]
                season_number = data[1].strip().split(' ')[1]
                episode_name = data[2].split(' [')[0]

                data = {
                    'season_number': season_number,
                    'season': season_name,
                    'episode_number': episode_number,
                    'episode': episode_name
                }
                videos.append(data)

        return videos


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

def to_strm(method):
    for crunchyroll_channel in channels:
        log_text = (f'Working {crunchyroll_channel}...')
        l.log("crunchyroll", log_text)

        crunchyroll = Crunchyroll(crunchyroll_channel)
        
        print(crunchyroll.channel_folder)

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

        last_episode = None
        for video in crunchyroll.videos:
            # Verifica si hay mutaciones especificadas para este canal.
            if crunchyroll_channel in mutate_values:
                for values in mutate_values[crunchyroll_channel]:
                    # Obtén el campo y el valor objetivo a mutar del diccionario 'values'.
                    field = values['field']
                    value = values['value']

                    # Si el valor actual en el campo corresponde al valor objetivo, reemplázalo.
                    if field in video and video[field] == value:
                        video[field] = values['replace']

            serie = crunchyroll.channel_folder
            serie_id = crunchyroll.channel_id
            season_number = video['season_number']
            season = video['season']
            episode_number = video['episode_number']
            episode = video['episode']

            data = {
                'serie' : serie,
                'serie_id' : serie_id,
                'season_number' : season_number,
                'season' : season,
                'episode_number' : episode_number,
                'episode' : episode
            }

            if not episode_number == '0' and not episode_number  == 0:
                url = f'{serie_id}-{episode}'

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

                    last_episode = file_content

        if jellyfin_preload_last_episode and (method == 'download' or method =='direct'):
            if 'http' in file_content:
                w.worker(file_content).preload()
        break