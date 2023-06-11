from flask import Flask, stream_with_context, request, Response, send_from_directory, send_file, redirect
from functions import make_clean_folder, write_file, tvinfo_scheme, host, port
from sanitize_filename import sanitize
import os
import json
import subprocess

#Reading config file
config_file = './plugins/twitch/config.json'
if not os.path.isfile(config_file):
    print("No config.json detected, using config.example.json. Please check this in current plugin folder")
    config_file = './plugins/twitch/config.example.json'

with open(
        config_file, 
        'r'
    ) as f:
    config = json.load(f)

media_folder = config["strm_output_folder"]
channels_list = config["channels_list_file"]
source_platform = "twitch"

if 'days_dateafter' in config:
    days_after = config["days_dateafter"]
    videos_limit = config['videos_limit']
else:
    days_after = "10"
    videos_limit = "10"

##Utils | Read and download full channels, generate nfo and strm files
def channels():
    channels_list_local = channels_list

    if not os.path.isfile(channels_list_local):
        print("No channel_list.json detected, using channel_list.example.json. Please check this in current plugin folder")
        channels_list_local = './plugins/twitch/channel_list.example.json'

    with open(
            channels_list_local, 
            'r'
        ) as f:
        channels = json.load(f)
    return channels

#¡¡¡¡¡ to_strm is mandatory start function, forced in cli.py under run function !!!!!
def to_strm(method):
    for twitch_channel in channels():
        print("Preparing channel {}".format(twitch_channel))

        #formating youtube URL and init channel_id
        twitch_channel_url = "https://www.twitch.tv/{}".format(twitch_channel)

        #Make a folder and inflate nfo file
        make_clean_folder("{}/{}".format(media_folder,  sanitize("{}".format(twitch_channel))))
        to_nfo({'twitch_channel' : "{}".format(twitch_channel), 'twitch_channel_folder' : twitch_channel})

        #Get current livestream
        print("Processing live video in channel")

        command = ['yt-dlp', 
                    '--print', '"%(id)s;%(title)s"', 
                    '--ignore-errors',
                    '--no-warnings',
                    '{}'.format(twitch_channel_url)]
    

        #print("Command \n {}".format(' '.join(command)))
        lines = subprocess.getoutput(' '.join(command)).split('\n')

        for line in lines:
            if line != "":
                if not 'ERROR' in line:
                    video_id = str(line).rstrip().split(';')[0]
                    video_name = str(line).rstrip().split(';')[1].split(" ")
                    try:
                        video_name.pop(3)
                    except:
                        pass
                    video_name = "{} [{}]".format(' '.join(video_name), video_id)
                    file_content = "http://{}:{}/{}/{}/{}".format(host, port, source_platform, method, "{}@{}".format(twitch_channel, video_id))
                    file_path = "{}/{}/{}.{}".format(media_folder,  sanitize("{}".format(twitch_channel)),  sanitize("!000-live-{}".format(twitch_channel)), "strm")

                    data = {
                        "video_id" : video_id, 
                        "video_name" : video_name
                    }
                    if not os.path.isfile(file_path):
                        write_file(file_path, file_content)

                    print(data)
                else:
                    try:
                        os.remove("{}/{}/{}.{}".format(media_folder,  sanitize("{}".format(twitch_channel)),  sanitize("!000-live-{}".format(twitch_channel)), "strm"))
                    except:
                        pass
    
    
        #Download /videos tab
        print("Processing videos tab in channel")

        command = ['yt-dlp', 
                    '--print', '"%(id)s;%(title)s;%(upload_date)s"', 
                    '--dateafter', "today-{}days".format(days_after),
                    '--playlist-start', '1', 
                    '--playlist-end', videos_limit, 
                    '--ignore-errors',
                    '--no-warnings',
                    '{}/{}'.format(twitch_channel_url,"videos")]
    

        #print("Command \n {}".format(' '.join(command)))
        lines = subprocess.getoutput(' '.join(command)).split('\n')

        for line in lines:
            if line != "":
                if not 'ERROR' in line:
                    video_id = str(line).rstrip().split(';')[0]
                    video_name = str(line).rstrip().split(';')[1].split(" ")
                    upload_date = str(line).rstrip().split(';')[2]
                    try:
                        video_name.pop(3)
                    except:
                        pass
                    video_name = "{} [{}]".format(' '.join(video_name), video_id)
                    file_content = "http://{}:{}/{}/{}/{}".format(host, port, source_platform, method, "{}@{}".format(twitch_channel, video_id))
                    file_path = "{}/{}/{}.{}".format(media_folder,  sanitize("{}".format(twitch_channel)),  sanitize("{}-{}".format(upload_date,video_name)), "strm")

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
                'https://www.twitch.tv/{}/{}'.format(params['twitch_channel'],"videos"),
                '--list-thumbnails',
                '--restrict-filenames',
                '--ignore-errors',
                '--no-warnings',
                '--no-download',
                '--playlist-items', '1']
    print("Command: \n {}".format(' '.join(command)))
    #The madness begins... 
    #No comments between lines, smoke a joint if you want understand it
    lines = subprocess.getoutput(' '.join(command)).split('\n')
    headers = []
    thumbnails = []
    for line in lines:
        line = ' '.join(line.split())
        if not '[' in line and not 'has no' in line:
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
    #print(thumbnails)
    poster = ""
    try:
        url_avatar_uncropped_index = next((index for (index, d) in enumerate(thumbnails) if d["ID"] == "0"), None)
        poster = thumbnails[url_avatar_uncropped_index]['URL']
        #print("Poster found")
    except:
        print("No poster detected")



    #get channel or playlist name
    command = ['yt-dlp', 
            'https://www.twitch.tv/{}'.format(params['twitch_channel']), 
            '--print', '"%(uploader)s"', 
            '--playlist-items', '1',
            '--restrict-filenames',
            '--ignore-errors',
            '--no-warnings',
            '--compat-options', 'no-youtube-channel-redirect',
            '--no-warnings']

    #print("Command {}".format(' '.join(command)))
    channel_name = subprocess.getoutput(' '.join(command))
    if 'ERROR' in channel_name:
        channel_name = params['twitch_channel']
    
    #print("Output: \n {}".format(channel_name))
    #no description available in twitch for this script at the moment
    description = ""

    output_nfo = tvinfo_scheme().format(
        channel_name,
        channel_name,
        channel_name,
        description,
        poster, poster,
        poster, poster,
        poster, poster,
        "",
        "Twitch",
        "Twitch"
    )

    
    if params['twitch_channel']:
        file_path = "{}/{}/{}.{}".format(media_folder, "{}".format(params['twitch_channel_folder']), "tvshow", "nfo")
        write_file(file_path, output_nfo)


##Video data stream | direct, bridge and download mode
def direct(twitch_id): #Sponsorblock doesn't work in this mode
    channel = twitch_id.split("@")[0]
    video_id = twitch_id.split("@")[1]
    twitch_url = subprocess.getoutput("yt-dlp -f best --no-warnings https://www.twitch.tv/videos/{} --get-url".format(video_id))
    #print("yt-dlp -f best --no-warnings https://www.twitch.tv/videos/{} --get-url".format(video_id))
    if 'ERROR' in twitch_url:
        twitch_url = subprocess.getoutput("yt-dlp -f best --no-warnings https://www.twitch.tv/videos/{} --get-url".format(video_id.replace('v','')))
        #print("yt-dlp -f best --no-warnings https://www.twitch.tv/videos/{} --get-url".format(video_id.replace('v','')))
        if 'ERROR' in twitch_url:
            twitch_url = subprocess.getoutput("yt-dlp -f best --no-warnings https://www.twitch.tv/{} --get-url".format(channel))
            #print("yt-dlp -f best --no-warnings https://www.twitch.tv/{} --get-url".format(channel))

    return redirect(twitch_url, code=301)
