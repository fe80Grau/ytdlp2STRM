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

        lines = w.worker(command).output().split('\n')
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

def to_strm(method):
    for crunchyroll_channel in channels:
        log_text = (f'Working {crunchyroll_channel}...')
        l.log("crunchyroll", log_text)

        crunchy = Crunchyroll(crunchyroll_channel)
        
        print(crunchy.channel_folder)
        for video in crunchy.videos:
            # Verifica si hay mutaciones especificadas para este canal.
            if crunchyroll_channel in mutate_values:
                for values in mutate_values[crunchyroll_channel]:
                    # Obtén el campo y el valor objetivo a mutar del diccionario 'values'.
                    field = values['field']
                    value = values['value']

                    # Si el valor actual en el campo corresponde al valor objetivo, reemplázalo.
                    if field in video and video[field] == value:
                        video[field] = values['replace']

            print(video)