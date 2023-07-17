from flask import Flask, stream_with_context, request, Response, send_from_directory, send_file, redirect
from functions import make_clean_folder, write_file, tvinfo_scheme, host, port
from sanitize_filename import sanitize
import os
import json
import time
import re
import platform
import subprocess
import fnmatch
import xml.etree.ElementTree as ET
import requests
from isodate import parse_duration
from bs4 import BeautifulSoup

source_platform = "pokemon_tv"
#Reading config file
config_file = './plugins/pokemon_tv/config.json'
if not os.path.isfile(config_file):
    print("No config.json detected, using config.example.json. Please check this in current plugin folder")
    config_file = './plugins/pokemon_tv/config.example.json'

with open(
        config_file, 
        'r'
    ) as f:
    config = json.load(f)

media_folder = config["strm_output_folder"]
channels_list = config["channels_list_file"]

def channels():
    github_base_url = "https://github.com/seiya-dev/pokemon-tv/tree/master/database/"
    github_raw_base_url = "https://raw.githubusercontent.com/seiya-dev/pokemon-tv/master/database/"
    # URL on the Github where the csv files are stored
    github_url = "{}{}".format(
         github_base_url, 
         config["pokemon_tv_language"]
    )  # change USERNAME, REPOSITORY and FOLDER with actual name

    result = requests.get(github_url)
    databases = json.loads(result.text)
    databases_json_files = []
    for i in databases['payload']['tree']['items']:
            databases_json_files.append(
                "{}{}/{}".format(
                    github_raw_base_url, 
                    config["pokemon_tv_language"], 
                    i['name']
                )
            )

    return databases_json_files

def to_nfo(params):
    pass

def to_strm(method):
    for channel in channels():
        pokemon_channel_folder = (
             channel
             .split('/')[-1]
             .split('-',1)[1]
             .split('.json')[0]
        )
        print(channel)

        seasson_api = json.loads(
             requests.get(channel)
             .text
        )

        make_clean_folder(
            "{}/{}/{}".format(
                media_folder, 
                "Pokemon",
                sanitize(
                    "{} - {}".format(
                        pokemon_channel_folder,
                        seasson_api["channel_name"]
                    )
                )
            )
        )

        for item in seasson_api["media"]:
            video_name = (
                "{} - {}".format(
                    "S{}E{}".format(
                        item['season'], 
                        item['episode']
                    ), 
                    item['title']
                )
            )

            file_content = item["stream_url"]
            file_path = (
                "{}/{}/{}/{}.{}".format(
                    media_folder,
                    "Pokemon",
                    sanitize(
                        "{} - {}".format(
                            pokemon_channel_folder,
                            seasson_api["channel_name"]
                        )
                    ),
                    sanitize(video_name),
                    "strm"
                )
            )

            make_clean_folder(
                "{}/{}/{}".format(
                    media_folder, 
                    "Pokemon",
                    sanitize(
                        "{} {} - {}".format(
                            "Pokemon",
                            pokemon_channel_folder,
                            seasson_api["channel_name"]
                        )
                    )
                )
            )

            if not os.path.isfile(file_path):
                write_file(file_path, file_content)

                
def direct(pokemon_tv_id): #Sponsorblock doesn't work in this mode
    pass
