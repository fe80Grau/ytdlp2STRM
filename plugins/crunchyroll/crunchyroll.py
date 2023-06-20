from flask import Flask, stream_with_context, request, Response, send_from_directory, send_file, redirect
from functions import make_clean_folder, write_file, tvinfo_scheme, host, port
from sanitize_filename import sanitize
import os
import json
import time
import platform
import subprocess
import fnmatch


# yt-dlp --sub-lang es-419 --cookies "D:\Crunchyroll\www.crunchyroll.com_cookies.txt" https://www.crunchyroll.com/es/series/GRMG8ZQZR/one-piece --print "%(season_number)s;%(season)s;%(episode_number)s;%(episode)s;%(webpage_url)s" --extractor-args "crunchyrollbeta:hardsub=jp-JP,es-ES" --no-download

source_platform = "crunchyroll"
#Reading config file
config_file = 'plugins/crunchyroll/config.json'
if not os.path.isfile(config_file):
    print("No config.json detected, using config.example.json. Please check this in current plugin folder")
    config_file = 'plugins/crunchyroll/config.example.json'

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
if 'proxy' in config:
    proxy = config['proxy']
    proxy_url = config['proxy_url']
else:
    proxy = False
    proxy_url = ""

##Utils | Read and download full channels, generate nfo and strm files
def set_proxy(command):
    if proxy:
        if proxy_url != "":
            command.append('--proxy')
            command.append(proxy_url)
        else:
            print("Proxy setted true but no proxy url, please check it in plugin config.json")



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

        last_episode_file = "{}/{}/{}.{}".format(media_folder,  sanitize("{}".format(crunchyroll_channel_folder)), "last_episode", "txt")
        last_episode = 0
        new_content = False
        if not os.path.isfile(last_episode_file):
            new_content = True
            write_file(last_episode_file, "0")
        else:
            with open(last_episode_file) as f:
                last_episode = f.readlines()
                f.close()
            
            last_episode = last_episode[0]

        command = ['yt-dlp', 
                    '--cookies', '{}'.format(cookies_file),
                    '--print', '%(season_number)s;%(season)s;%(episode_number)s;%(episode)s;%(webpage_url)s;%(playlist_autonumber)s', 
                    '--no-download',
                    '--no-warnings',
                    '--match-filter', 'language={}'.format(audio_language),
                    '--extractor-args', 'crunchyrollbeta:hardsub={}'.format(subtitle_language),
                    '{}'.format(crunchyroll_channel_url)]
    
        set_proxy(command)

        if not new_content:
            next_episode = int(last_episode) + 1
            command.append('--playlist-start')
            command.append('{}'.format(next_episode))


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
                    playlist_count = (line).rstrip().split(';')[5]

                    #print(playlist_count)
               
                    video_name = "{} - {}".format("S{}E{}".format(season_number, episode_number), episode)


                    file_content = "http://{}:{}/{}/{}/{}".format(host, port, source_platform, method, url)
                    file_path = "{}/{}/{}/{}.{}".format(media_folder,  sanitize("{}".format(crunchyroll_channel_folder)),  sanitize("S{} - {}".format(season_number, season)), sanitize(video_name), "strm")
                    make_clean_folder("{}/{}/{}".format(media_folder,  sanitize("{}".format(crunchyroll_channel_folder)),  sanitize("S{} - {}".format(season_number, season))))
                    data = {
                        "video_name" : video_name
                    }
                    if not os.path.isfile(file_path):
                        write_file(file_path, file_content)
                    if new_content:
                        write_file(last_episode_file, playlist_count)
                    else:
                        sum_episode = int(last_episode) + int(playlist_count)
                        write_file(last_episode_file,str(sum_episode))
                    #print(data)

                if not line: break
                
        finally:
            process.kill()


    return True 


##Video data stream | direct, bridge and download mode
def direct(crunchyroll_id): #Sponsorblock doesn't work in this mode
    #crunchyroll_url = subprocess.getoutput("yt-dlp -f best --cookies {} --no-warnings --match-filter language={} --extractor-args crunchyrollbeta:hardsub={} https://www.crunchyroll.com/{} --get-url".format(cookies_file, audio_language, subtitle_language, crunchyroll_id.replace('_','/')))
    
    command = ['yt-dlp', 
                '-f', 'best',
                '--cookies', '"{}"'.format(cookies_file),
                '--no-warnings',
                '--match-filter', '"language={}"'.format(audio_language),
                '--extractor-args', '"crunchyrollbeta:hardsub={}"'.format(subtitle_language),
                'https://www.crunchyroll.com/{}'.format(crunchyroll_id.replace('_','/')),
                '--get-url']
    
    set_proxy(command)
    #print(' '.join(command))
    crunchyroll_url = subprocess.getoutput(' '.join(command))
    #print(crunchyroll_url)
    #print(crunchyroll_url)
    return redirect(crunchyroll_url, code=301)