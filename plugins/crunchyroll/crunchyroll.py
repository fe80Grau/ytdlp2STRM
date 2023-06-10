from flask import Flask, stream_with_context, request, Response, send_from_directory, send_file, redirect
from functions import make_clean_folder, write_file, tvinfo_scheme, host, port
from sanitize_filename import sanitize
import os
import json
import time
import platform
import subprocess


# yt-dlp --sub-lang es-419 --cookies "D:\Crunchyroll\www.crunchyroll.com_cookies.txt" https://www.crunchyroll.com/es/series/GRMG8ZQZR/one-piece --print "%(season_number)s;%(season)s;%(episode_number)s;%(episode)s;%(webpage_url)s" --extractor-args "crunchyrollbeta:hardsub=jp-JP,es-ES" --no-download

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
cookies_file = config["crunchyroll_cookies_file"]
subtitle_language = config["crunchyroll_subtitle_language"]
audio_language = config['crunchyroll_audio_language']

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

        #Make seasons folders Get all videos and subtitle from serie
        print("Processing videos in channel")

        command = ['yt-dlp', 
                    '--cookies', '{}'.format(cookies_file),
                    '--print', '%(season_number)s;%(season)s;%(episode_number)s;%(episode)s;%(webpage_url)s', 
                    '--no-download',
                    '--no-warnings',
                    '--match-filter', 'language={}'.format(audio_language),
                    '--extractor-args', 'crunchyrollbeta:hardsub={}'.format(subtitle_language),
                    '{}'.format(crunchyroll_channel_url)]
    


        #print("Command \n {}".format(' '.join(command)))
        #lines = subprocess.getoutput(' '.join(command)).split('\n')

        process = subprocess.Popen(command, stdout=subprocess.PIPE, universal_newlines=True)
        try:
            for line in iter(process.stdout.readline, b''):
                #print(line)
                if line != "" and not 'ERROR' in line and not 'WARNING' in line:
                    
                    season_number = str(line).rstrip().split(';')[0].zfill(2)
                    season = str(line).rstrip().split(';')[1]
                    episode_number = (line).rstrip().split(';')[2].zfill(4)
                    episode = (line).rstrip().split(';')[3]
                    url = (line).rstrip().split(';')[4].replace('https://www.crunchyroll.com/','').replace('/','_')


                    video_name = "{} - {}".format("S{}E{}".format(season_number, episode_number), episode)


                    file_content = "http://{}:{}/{}/{}/{}".format(host, port, source_platform, method, url)
                    file_path = "{}/{}/{}/{}.{}".format(media_folder,  sanitize("{}".format(crunchyroll_channel_folder)),  sanitize("S{} - {}".format(season_number, season)), sanitize(video_name), "strm")
                    make_clean_folder("{}/{}/{}".format(media_folder,  sanitize("{}".format(crunchyroll_channel_folder)),  sanitize("S{} - {}".format(season_number, season))))
                    data = {
                        "video_name" : video_name
                    }
                    if not os.path.isfile(file_path):
                        write_file(file_path, file_content)

                    print(data)

                if not line: break
                
        finally:
            process.kill()


    return True 


##Video data stream | direct, bridge and download mode
def direct(crunchyroll_id): #Sponsorblock doesn't work in this mode
    crunchyroll_url = subprocess.getoutput("yt-dlp -f best --cookies {} --no-warnings --match-filter language={} --extractor-args crunchyrollbeta:hardsub={} https://www.crunchyroll.com/{} --get-url".format(cookies_file, audio_language, subtitle_language, crunchyroll_id.replace('_','/')))
    #print(crunchyroll_url)
    return redirect(crunchyroll_url, code=301)