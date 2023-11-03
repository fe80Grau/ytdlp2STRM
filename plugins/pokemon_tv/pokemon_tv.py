from sanitize_filename import sanitize
import os
import json
import requests
from clases.config import config as c
from clases.folders import folders as f
from clases.nfo import nfo as n


## -- LOAD CONFIG AND CHANNELS FILES
ytdlp2strm_config = c.config(
    './config/config.json'
).get_config()

config = c.config(
    './plugins/pokemon_tv/config.json'
).get_config()


source_platform = "pokemon_tv"
media_folder = config["strm_output_folder"]
channels_list = config["channels_list_file"]
## -- END

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
        if ('series' in i['name']
            or 'movies' in i['name']):
            databases_json_files.append(
                "{}{}/{}".format(
                    github_raw_base_url, 
                    config["pokemon_tv_language"], 
                    i['name']
                )
            )

    return databases_json_files


def to_strm(method):
    for channel in channels():
        print(channel)

        seasson_type = "serie/Pokemon"
        if 'movies' in channel:
            seasson_type = "movies"

        nfo_type = "episode" if seasson_type != "movies" else "movie"

        pokemon_channel_folder = (
             channel
             .split('/')[-1]
             .split('-',1)[1]
             .split('.json')[0]
        ) if seasson_type != "movies" else "Pokemon"
        
        seasson_api = json.loads(
             requests.get(channel)
             .text
        )

        f.folders().make_clean_folder(
            "{}/{}/{}/{}".format(
                media_folder, 
                "Pokemon",
                seasson_type,
                sanitize(
                    "{} - {}".format(
                        pokemon_channel_folder,
                        seasson_api["channel_name"]
                    )
                )
            ),
            False,
            config
        )

        for item in seasson_api["media"]:
            video_name = (
                "{} - {}".format(
                    "S{}E{}".format(
                        item['season'].zfill(2), 
                        item['episode'].zfill(2)
                    ), 
                    item['title']
                )
            ) if seasson_type != "movies" else (
                "{} - {}".format(
                    "Pokemon", 
                    item['title']
                )
            )

            if 'stream_url' in item:
                file_content = item['stream_url']
            else:
                file_content = item["offline_url"]
            file_path = (
                "{}/{}/{}/{}/{}.{}".format(
                    media_folder,
                    "Pokemon",
                    seasson_type,
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

            f.folders().make_clean_folder(
                "{}/{}/{}/{}".format(
                    media_folder, 
                    "Pokemon",
                    seasson_type,
                    sanitize(
                        "{} - {}".format(
                            pokemon_channel_folder,
                            seasson_api["channel_name"]
                        )
                    )
                ),
                False,
                config
            )
            ## -- BUILD VIDEO NFO FILE
            n.nfo(
                nfo_type,
                "{}/{}/{}/{}".format(
                    media_folder, 
                    "Pokemon",
                    seasson_type,
                    sanitize(
                        "{} - {}".format(
                            pokemon_channel_folder,
                            seasson_api["channel_name"]
                        )
                    )
                ),
                {
                    "item_name" : sanitize(video_name),
                    "title" : item['title'],
                    "plot" : item['description'],
                    "season" : item['season'],
                    "episode" : item['episode'],
                    "preview" : item['images']['large']
                }
            ).make_nfo()


            if not os.path.isfile(file_path):
                f.folders().write_file(file_path, file_content)

                
def direct(pokemon_tv_id): #Sponsorblock doesn't work in this mode
    pass
