from flask import Flask, stream_with_context, request, Response, send_from_directory, send_file, redirect
from functions import make_clean_folder, write_file, tvinfo_scheme, host, port
from sanitize_filename import sanitize
import os
import json
import time
import platform
import subprocess

#Reading config file
config_file = './plugins/youtube/config.json'
if not os.path.isfile(config_file):
    print("No config.json detected, using config.example.json. Please check this in current plugin folder")
    config_file = './plugins/youtube/config.example.json'

with open(
        config_file, 
        'r'
    ) as f:
    config = json.load(f)

media_folder = config["strm_output_folder"]
channels_list = config["channels_list_file"]
days_dateafter = config["days_dateafter"]
videos_limit = config["videos_limit"]
source_platform = "youtube"
if 'proxy' in config:
    proxy = config['proxy']
    proxy_url = config['proxy_url']
else:
    proxy = False
    proxy_url = ""

##Utils | Read and download full channels, generate nfo and strm files
def channels():
    channels_list_local = channels_list

    if not os.path.isfile(channels_list_local):
        print("No channel_list.json detected, using channel_list.example.json. Please check this in current plugin folder")
        channels_list_local = './plugins/youtube/channel_list.example.json'

    with open(
            channels_list_local, 
            'r'
        ) as f:
        channels = json.load(f)
    return channels

def channel_strm(youtube_channel, youtube_channel_url, method):
    channel_id = False

    command = ['yt-dlp', 
                '--compat-options', 'no-youtube-channel-redirect',
                '--compat-options', 'no-youtube-unavailable-videos',
                '--restrict-filenames',
                '--ignore-errors',
                '--no-warnings',
                '--playlist-start', '1', 
                '--playlist-end', '1', 
                '--print', 'channel_url', 
                youtube_channel_url]
    set_proxy(command)

    lines = subprocess.getoutput(' '.join(command)).split('\n')
    #print("Command: \n {}".format(' '.join(command)))
    #print("Output: \n {}".format(lines))

    for line in lines:
        if 'channel' in line:
            channel_id = line.rstrip().split('/')[-1]
    
    #print("Channel ID value: {}".format(channel_id))
    if not channel_id:
        print("No channel ID Found, Research with no video tab")

        youtube_channel_url = "https://www.youtube.com/{}".format(youtube_channel)
        command = ['yt-dlp', 
                    '--compat-options', 'no-youtube-channel-redirect',
                    '--compat-options', 'no-youtube-unavailable-videos',
                    '--restrict-filenames',
                    '--ignore-errors',
                    '--no-warnings',
                    '--playlist-start', '1', 
                    '--playlist-end', '1', 
                    '--print', 'channel_url', 
                    youtube_channel_url]
        #print(' '.join(command))
        set_proxy(command)
                
        lines = subprocess.getoutput(' '.join(command)).split('\n')
        for line in lines:
            if 'channel' in line:
                channel_id = line.rstrip().split('/')[-1]
    
    #Clearing channel folder name
    youtube_channel_folder = youtube_channel.replace('/user/','@').replace('/streams','')
    #Make a folder and inflate nfo file
    make_clean_folder("{}/{}".format(media_folder,  sanitize("{} [{}]".format(youtube_channel_folder,channel_id))))
    to_nfo({'youtube_channel' : "channel/{}".format(channel_id), 'youtube_channel_folder' : youtube_channel_folder})

    #Get las 60 days videos in channel
    print("Processing videos in channel")

    command = ['yt-dlp', 
                '--compat-options', 'no-youtube-channel-redirect',
                '--compat-options', 'no-youtube-unavailable-videos',
                '--print', '"%(id)s;%(title)s"', 
                '--dateafter', "today-{}days".format(days_dateafter), 
                '--playlist-start', '1', 
                '--playlist-end', videos_limit, 
                '--ignore-errors',
                '--no-warnings',
                '{}'.format(youtube_channel_url)]

    set_proxy(command)


    if config['days_dateafter'] == "0":
        command.pop(7)
        command.pop(7)

    #print("Command \n {}".format(' '.join(command)))
    lines = subprocess.getoutput(' '.join(command)).split('\n')

    for line in lines:
        if line != "":
            video_id = str(line).rstrip().split(';')[0]
            video_name = "{} [{}]".format(str(line).rstrip().split(';')[1], video_id)
            file_content = "http://{}:{}/{}/{}/{}".format(host, port, source_platform, method, video_id)
            file_path = "{}/{}/{}.{}".format(media_folder,  sanitize("{} [{}]".format(youtube_channel_folder,channel_id)),  sanitize(video_name), "strm")

            data = {
                "video_id" : video_id, 
                "video_name" : video_name
            }
            if not os.path.isfile(file_path):
                write_file(file_path, file_content)

            print(data)


def keyword_strm(keyword, method):
    command = ['yt-dlp', 
                '-f', 'best', 'ytsearch10:["{}"]'.format(keyword),
                '--compat-options', 'no-youtube-channel-redirect',
                '--compat-options', 'no-youtube-unavailable-videos',
                '--no-warning',
                '--print', '"%(id)s;%(channel_id)s;%(uploader_id)s;%(title)s"']
                
    set_proxy(command)
    #print(' '.join(command))

    lines = subprocess.getoutput(' '.join(command)).split('\n')
    for line in lines:
        if line != "" and not 'ERROR' in line:
            video_id = str(line).rstrip().split(';')[0]
            channel_id = str(line).rstrip().split(';')[1]
            video_name = str(line).rstrip().split(';')[3]
            youtube_channel = str(line).rstrip().split(';')[2]
            youtube_channel_folder = youtube_channel.replace('/user/','@').replace('/streams','')
            file_content = "http://{}:{}/{}/{}/{}".format(host, port, source_platform, method, video_id)
            file_path = "{}/{}/{}.{}".format(media_folder,  sanitize("{} [{}]".format(youtube_channel_folder,channel_id)),  sanitize(video_name), "strm")

            make_clean_folder("{}/{}".format(media_folder,  sanitize("{} [{}]".format(youtube_channel_folder,channel_id))))
            to_nfo({'youtube_channel' : "channel/{}".format(channel_id), 'youtube_channel_folder' : youtube_channel_folder})


            data = {
                "video_id" : video_id, 
                "video_name" : video_name
            }
            if not os.path.isfile(file_path):
                write_file(file_path, file_content)

            print(data)

#¡¡¡¡¡ to_strm is mandatory start function, forced in cli.py under run function !!!!!
def to_strm(method):
    for youtube_channel in channels():
        print("Preparing channel {}".format(youtube_channel))

        #formating youtube URL and init channel_id
        youtube_channel_url = "https://www.youtube.com/{}/videos".format(youtube_channel)
        #Cases like /user/xbox
        if not "@" in youtube_channel:
            youtube_channel_url = "https://www.youtube.com{}".format(youtube_channel)

        if 'list-' in youtube_channel:
            youtube_channel_url = "https://www.youtube.com/playlist?list={}".format(youtube_channel.split('list-')[1])

        if '/streams' in youtube_channel:
            method = 'direct'

        if 'keyword-' in youtube_channel:
            keyword = youtube_channel.split('-')
            if len(keyword) > 1:
                keyword_strm(keyword[1], method)
        else:
            channel_strm(youtube_channel, youtube_channel_url,method)


    return True 

def to_nfo(params):
    print("Inflating  nfo file..")
    #Table thumbnails
    c = 0
    command = ['yt-dlp', 
                'https://www.youtube.com/{}'.format(params['youtube_channel']),
                '--list-thumbnails',
                '--restrict-filenames',
                '--ignore-errors',
                '--no-warnings',
                '--playlist-items', '0']
    set_proxy(command)

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
    channel_id = params['youtube_channel'].split('/')[-1]
    #print("Channel ID {}".format(channel_id))


    #get channel or playlist name
    if 'list-' in params['youtube_channel_folder']:
        command = ['yt-dlp', 
                'https://www.youtube.com/{}'.format(params['youtube_channel']), 
                '--compat-options', 'no-youtube-unavailable-videos',
                '--print', '"%(playlist_title)s"', 
                '--playlist-items', '1',
                '--restrict-filenames',
                '--ignore-errors',
                '--no-warnings',
                '--compat-options', 'no-youtube-channel-redirect',
                '--no-warnings']
    else:
        command = ['yt-dlp', 
                    'https://www.youtube.com/{}'.format(params['youtube_channel']),
                    '--compat-options', 'no-youtube-unavailable-videos',
                    '--print', '"%(channel)s"',
                    '--restrict-filenames',
                    '--ignore-errors',
                    '--no-warnings',
                    '--playlist-items', '1',
                    '--compat-options', 'no-youtube-channel-redirect',
                    '--no-warnings']
    set_proxy(command)

    #print("Command {}".format(' '.join(command)))
    channel_name = subprocess.getoutput(' '.join(command))
    #print("Output: \n {}".format(channel_name))
    #get description
    description = ""
    if platform.system() != "Linux":
        command = ['yt-dlp', 
                    'https://www.youtube.com/{}'.format(params['youtube_channel']), 
                    '--write-description', 
                    '--playlist-items', '0',
                    '--output', '"{}/{}.description"'.format(media_folder, channel_name)
                    ]
        set_proxy(command)

        command = command + ['>', '/dev/null', '2>&1','&&', 'cat', '"{}/{}.description"'.format(media_folder, channel_name)]
        
        #print("Command \n {}".format(' '.join(command)))
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
        "Youtube",
        "Youtube"
    )

    
    if channel_id:
        file_path = "{}/{}/{}.{}".format(media_folder, "{} [{}]".format(params['youtube_channel_folder'],channel_id), "tvshow", "nfo")
        write_file(file_path, output_nfo)

def set_proxy(command):
    if proxy:
        if proxy_url != "":
            command.append('--proxy')
            command.append(proxy_url)
        else:
            print("Proxy setted true but no proxy url, please check it in plugin config.json")


##Video data stream | direct, bridge and download mode
def direct(youtube_id): #Sponsorblock doesn't work in this mode
    command = ['yt-dlp', 
                '-f', 'best',
                '--no-warnings',
                '--get-url', 
                youtube_id]
    set_proxy(command)
    youtube_url = subprocess.getoutput(' '.join(command))
    return redirect(youtube_url, code=301)

def bridge(youtube_id):
    def generate():
        startTime = time.time()
        buffer = []
        sentBurst = False
        if config["sponsorblock"]:
            command = ['yt-dlp', '-o', '-', '-f', 'bv*+ba+ba.2', '--sponsorblock-remove',  config['sponsorblock_cats'], '--restrict-filenames', youtube_id]
        else:
            command = ['yt-dlp', '-o', '-', '-f', 'bv*+ba+ba.2', '--restrict-filenames', youtube_id]

        set_proxy(command)


        process = subprocess.Popen(command, stdout=subprocess.PIPE)
        try:
            while True:
                # Get some data from ffmpeg
                line = process.stdout.read(1024)

                # We buffer everything before outputting it
                buffer.append(line)

                # Minimum buffer time, 3 seconds
                if sentBurst is False and time.time() > startTime + 3 and len(buffer) > 0:
                    sentBurst = True

                    for i in range(0, len(buffer) - 2):
                        print("Send initial burst #", i)
                        yield buffer.pop(0)

                elif time.time() > startTime + 3 and len(buffer) > 0:
                    yield buffer.pop(0)

                process.poll()
                if isinstance(process.returncode, int):
                    if process.returncode > 0:
                        print('yt-dlp Error', process.returncode)
                    break
        finally:
            process.kill()

    return Response(stream_with_context(generate()), mimetype = "video/mp4") 

def download(youtube_id):
    if config["sponsorblock"]:
        command = ['yt-dlp', '-f', 'bv*+ba+ba.2', '--sponsorblock-remove',  config['sponsorblock_cats'], '--restrict-filenames', youtube_id]
    else:
        command = ['yt-dlp', '-f', 'bv*+ba+ba.2', '--restrict-filenames', youtube_id]
    set_proxy(command)
    process = subprocess.call(command)
    filename = subprocess.getoutput("yt-dlp --print filename --restrict-filenames {}".format(youtube_id))
    return send_file(filename)
