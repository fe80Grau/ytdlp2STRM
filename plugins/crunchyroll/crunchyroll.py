from flask import Flask, stream_with_context, request, Response, send_from_directory, send_file, redirect
from functions import make_clean_folder, write_file, tvinfo_scheme, host, port
from sanitize_filename import sanitize
import os
import json
import time
import platform
import subprocess

source_platform = "crunchyroll"
#Reading config file
config_file = './plugins/crunchyroll/config.json'
if not os.path.isfile(config_file):
    print("No config.json detected, using config.example.json. Please check this in current plugin folder")
    config_file = './plugins/crunchyroll/config.example.json'

with open(
        config_file, 
        'r'
    ) as f:
    config = json.load(f)

media_folder = config["strm_output_folder"]
channels_list = config["channels_list_file"]
days_dateafter = config["days_dateafter"]
videos_limit = config["videos_limit"]


##Utils | Read and download full channels, generate nfo and strm files
def channels():
    channels_list_local = channels_list

    if not os.path.isfile(channels_list_local):
        print("No channel_list.json detected, using channel_list.example.json. Please check this in current plugin folder")
        channels_list_local = './plugins/crunchyroll/channel_list.example.json'

    with open(
            channels_list_local, 
            'r'
        ) as f:
        channels = json.load(f)
    return channels

#¡¡¡¡¡ to_strm is mandatory start function, forced in cli.py under run function !!!!!
def to_strm(method):
    for crunchyroll_channel in channels():
        print("Preparing channel {}".format(crunchyroll_channel))

        #formating crunchyroll URL and init channel_id
        crunchyroll_channel_url = "https://www.crunchyroll.com/{}".format(crunchyroll_channel)


        #Clearing channel folder name
        crunchyroll_channel_folder = crunchyroll_channel.split('/')[-1]
        #Make a folder and inflate nfo file
        make_clean_folder("{}/{}".format(media_folder,  sanitize("{}".format(crunchyroll_channel_folder))))
        to_nfo({'crunchyroll_channel' : crunchyroll_channel, 'crunchyroll_channel_folder' : crunchyroll_channel_folder})

        #Make seasons folders Get all videos and subtitle from serie
        print("Processing videos in channel")

        command = ['yt-dlp', 
                    '--print', '"%(id)s;%(title)s"', 
                    '--ignore-errors',
                    '--no-warnings',
                    '{}'.format(crunchyroll_channel_url)]
    


        #print("Command \n {}".format(' '.join(command)))
        lines = subprocess.getoutput(' '.join(command)).split('\n')

        for line in lines:
            if line != "":
                video_id = str(line).rstrip().split(';')[0]
                video_name = "{} [{}]".format(str(line).rstrip().split(';')[1], video_id)
                file_content = "http://{}:{}/{}/{}/{}".format(host, port, source_platform, method, video_id)
                file_path = "{}/{}/{}.{}".format(media_folder,  sanitize("{} [{}]".format(crunchyroll_channel_folder,channel_id)),  sanitize(video_name), "strm")

                data = {
                    "video_id" : video_id, 
                    "video_name" : video_name
                }
                if not os.path.isfile(file_path):
                    write_file(file_path, file_content)

                print(data)

    return True 

def to_nfo(params):
    print("Inflating  nfo file..")
    #Table thumbnails
    c = 0
    command = ['yt-dlp', 
                'https://www.crunchyroll.com/{}'.format(params['crunchyroll_channel']),
                '--list-thumbnails',
                '--restrict-filenames',
                '--ignore-errors',
                '--no-warnings',
                '--playlist-items', '0']
    #print("Command: \n {}".format(' '.join(command)))
    #The madness begins... 
    #No comments between lines, smoke a joint if you want understand it
    lines = subprocess.getoutput(' '.join(command)).split('\n')
    headers = []
    thumbnails = []
    for line in lines:
        line = ' '.join(line.split())
        if not '[' in line:
            data = line.split(' ')
            if c == 0:
                headers = data
            else:
                if not 'ID' in data[0]:
                    row = {}
                    for i, d in enumerate(data):
                        row[headers[i]] = d
                    thumbnails.append(row)
            c += 1
    #finally...

    #get images
    poster = ""
    try:
        url_avatar_uncropped_index = next((index for (index, d) in enumerate(thumbnails) if d["ID"] == "avatar_uncropped"), None)
        poster = thumbnails[url_avatar_uncropped_index]['URL']
        #print("Poster found")
    except:
        print("No poster detected")

    landscape = ""
    try:
        url_max_landscape_index = next((index for (index, d) in enumerate(thumbnails) if d["ID"] == "banner_uncropped"), None)
        landscape = thumbnails[url_max_landscape_index-1]['URL']
        #print("Landscape found")
    except:
        print("No landscape detected")

    #get channel id
    channel_id = params['crunchyroll_channel'].split('/')[-1]
    #print("Channel ID {}".format(channel_id))


    #get channel or playlist name
    if 'list-' in params['crunchyroll_channel_folder']:
        command = ['yt-dlp', 
                'https://www.crunchyroll.com/{}'.format(params['crunchyroll_channel']), 
                '--compat-options', 'no-crunchyroll-unavailable-videos',
                '--print', '"%(playlist_title)s"', 
                '--playlist-items', '1',
                '--restrict-filenames',
                '--ignore-errors',
                '--no-warnings',
                '--compat-options', 'no-crunchyroll-channel-redirect',
                '--no-warnings']
    else:
        command = ['yt-dlp', 
                    'https://www.crunchyroll.com/{}'.format(params['crunchyroll_channel']),
                    '--compat-options', 'no-crunchyroll-unavailable-videos',
                    '--print', '"%(channel)s"',
                    '--restrict-filenames',
                    '--ignore-errors',
                    '--no-warnings',
                    '--playlist-items', '1',
                    '--compat-options', 'no-crunchyroll-channel-redirect',
                    '--no-warnings']
    #print("Command {}".format(' '.join(command)))
    channel_name = subprocess.getoutput(' '.join(command))
    #print("Output: \n {}".format(channel_name))
    #get description
    description = ""
    if platform.system() == "Linux":
        command = ['yt-dlp', 
                    'https://www.crunchyroll.com/{}'.format(params['crunchyroll_channel']), 
                    '--write-description', 
                    '--playlist-items', '0',
                    '--output', '"{}/{}.description"'.format(media_folder, channel_name),
                    '>', '/dev/null', '2>&1', 
                    '&&', 'cat', '"{}/{}.description"'.format(media_folder, channel_name) 
                    ]
        print("Command \n {}".format(' '.join(command)))
        description = subprocess.getoutput(' '.join(command))
        print("Output \n {}".format(description))
        try:
            os.remove("{}/{}.description".format(media_folder,channel_name))
        except:
            pass

    else:
        print("Descriptions only works in Linux system at the moment")

    output_nfo = tvinfo_scheme().format(
        channel_name,
        channel_name,
        channel_name,
        description,
        landscape, landscape,
        poster, poster,
        poster, poster,
        channel_id,
        "crunchyroll",
        "crunchyroll"
    )

    
    if channel_id:
        file_path = "{}/{}/{}.{}".format(media_folder, "{} [{}]".format(params['crunchyroll_channel_folder'],channel_id), "tvshow", "nfo")
        write_file(file_path, output_nfo)

##Video data stream | direct, bridge and download mode
def direct(crunchyroll_id): #Sponsorblock doesn't work in this mode
    crunchyroll_url = subprocess.getoutput("yt-dlp -f best --no-warnings {} --get-url".format(crunchyroll_id))
    return redirect(crunchyroll_url, code=301)