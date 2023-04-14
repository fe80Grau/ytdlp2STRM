from datetime import datetime
import platform
import argparse, sys
import subprocess
import json
import glob
import os
from sanitize_filename import sanitize

#Reading config file
with open('config.json', 'r') as f:
    config = json.load(f)


media_folder = config["strm_output_folder"]
host = config["ytdlp2strm_host"]
port = config["ytdlp2strm_port"]
channels_list_file = config["ytdlp2strm_channels_list_file"]

days_dateafter = config["ytdlp2strm_days_dateafter"]
videos_limit = config["ytdlp2strm_videos_limit"]


tvinfo_scheme = """<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>
<tvshow>
    <title>{}</title>
    <originaltitle>{}</originaltitle>
    <showtitle>{}</showtitle>
    <season>1</season>
    <displayseason>-1</displayseason>
    <displayepisode>-1</displayepisode>
    <plot>{}</plot>
    <thumb spoof="" cache="" aspect="landscape" preview="{}">{}</thumb>
    <thumb spoof="" cache="" aspect="poster" preview="{}">{}</thumb>
    <thumb spoof="" cache="" season="1" type="season" aspect="poster" preview="{}">{}</thumb>
    <mpaa></mpaa>
    <uniqueid type="YoutubeMetadata" default="true">{}</uniqueid>    
    <genre>{}</genre>
    <studio>{}</studio>
</tvshow>
"""

def channels():
    channels = []
    with open(channels_list_file, 'r') as f:
        channels = json.load(f)
    return channels

def makecleanfolder(folder):
    print("Clearing {} folder...".format(folder))
    try:
        if(os.path.isdir(folder)):
            #items = glob.glob(  "{}/*".format(glob.escape(folder)) )
            #for r in items:
            #    os.remove(r)
            print("exist")
        else:
            os.mkdir(folder)
    except Exception as e:
        print(e)
        return False
    return True

def writeFile(file, content):
    try:
        f = open(file, "w")
        f.write(content)
        f.close()
    except Exception as e:
        print(e)
        return False
    return True

def inflate_nfo(source_platform="youtube", params=""):
    print("Inflating  nfo file..")
    if source_platform == "youtube":
        #Table thumbnails
        c = 0
        command = ['yt-dlp', 
                    'https://www.youtube.com/{}'.format(params['youtube_channel']),
                    '--list-thumbnails',
                    '--restrict-filenames',
                    '--ignore-errors',
                    '--no-warnings',
                    '--playlist-items', '0']
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
        except:
            print("No poster detected")

        landscape = ""
        try:
            url_max_landscape_index = next((index for (index, d) in enumerate(thumbnails) if d["ID"] == "banner_uncropped"), None)
            landscape = thumbnails[url_avatar_uncropped_index-1]['URL']
        except:
            print("No landscape detected")

        #get channel id
        channel_id = params['youtube_channel'].split('/')[-1]


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
        channel_name = subprocess.getoutput(' '.join(command))

        #get description
        description = ""
        if platform.system() == "Linux":
            command = ['yt-dlp', 
                        'https://www.youtube.com/{}'.format(params['youtube_channel']), 
                        '--write-description', 
                        '--playlist-items', '0',
                        '--output', '"{}.description"'.format(channel_name),
                        '>', '/dev/null', '2>&1', 
                        '&&', 'cat', '"{}.description"'.format(channel_name) 
                        ]
            description = subprocess.getoutput(' '.join(command))
            try:
                os.remove("{}.description".format(channel_name))
            except:
                pass
        else:
            print("Descriptions only works in Linux system at the moment")

        output_nfo = tvinfo_scheme.format(
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
            writeFile(file_path, output_nfo)

def make_files_strm(source_platform="youtube", method="stream"):
    if source_platform == "youtube":
        for youtube_channel in channels():
            print("Preparing channel {}".format(youtube_channel))

            #formating youtube URL and init channel_id
            youtube_channel_url = "https://www.youtube.com/{}/videos".format(youtube_channel)
            channel_id = False
            #Cases like /user/xbox
            if not "@" in youtube_channel:
                youtube_channel_url = "https://www.youtube.com{}".format(youtube_channel)

            if 'list-' in youtube_channel:
                youtube_channel_url = "https://www.youtube.com/playlist?list={}".format(youtube_channel.split('list-')[1])



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
            print(' '.join(command))

            lines = subprocess.getoutput(' '.join(command)).split('\n')
            for line in lines:
                if 'channel' in line:
                    channel_id = line.rstrip().split('/')[-1]
            

            if not channel_id:
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
                print(' '.join(command))
                lines = subprocess.getoutput(' '.join(command)).split('\n')
                for line in lines:
                    if 'channel' in line:
                        channel_id = line.rstrip().split('/')[-1]
            
            #Clearing channel folder name
            youtube_channel_folder = youtube_channel.replace('/user/','@')
            #Make a folder and inflate nfo file
            makecleanfolder("{}/{}".format(media_folder,  sanitize("{} [{}]".format(youtube_channel_folder,channel_id))))
            inflate_nfo("youtube", {'youtube_channel' : "channel/{}".format(channel_id), 'youtube_channel_folder' : youtube_channel_folder})

            #Get las 60 days videos in channel
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
            lines = subprocess.getoutput(' '.join(command)).split('\n')

            for line in lines:
                
                video_id = str(line).rstrip().split(';')[0]
                video_name = "{} [{}]".format(str(line).rstrip().split(';')[1], video_id)
                file_content = "http://{}:{}/{}/{}/{}".format(host, port, source_platform, method, video_id)
                file_path = "{}/{}/{}.{}".format(media_folder,  sanitize("{} [{}]".format(youtube_channel_folder,channel_id)),  sanitize(video_name), "strm")

                data = {
                    "video_id" : video_id, 
                    "video_name" : video_name
                }
                if not os.path.isfile(file_path):
                    writeFile(file_path, file_content)

                print(data)

    return True
                

if __name__ == "__main__":
    parser=argparse.ArgumentParser()

    parser.add_argument('--m', help='Método a ejecutar')
    parser.add_argument('--p', help='Parámetros para el método a ejecutar. Separado por comas.')

    args=parser.parse_args()

    method = args.m if args.m != None else "error"
    params = args.p.split(',') if args.p != None else None


    now = datetime.now()
    dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
    print(dt_string)
    print("Running {} with {} params".format(method, params))
    r = False
    if params != None:
        r = getattr(sys.modules[__name__], method)(*params)
    else:
        call = getattr(sys.modules[__name__], method)
        r = call()

    print(r)
