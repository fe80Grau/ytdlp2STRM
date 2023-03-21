from datetime import datetime
import argparse, sys
import subprocess
import json
import glob
import os


#Reading config file
with open('config.json', 'r') as f:
    config = json.load(f)


media_folder = config["strm_output_folder"]
host = config["ytdlp2strm_host"]
port = config["ytdlp2strm_port"]
channels_list_file = config["ytdlp2strm_channels_list_file"]

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


def createSTRM(file, content):
    try:
        f = open(file, "w")
        f.write(content)
        f.close()
    except:
        return False
    return True


def make_files_strm(platform="youtube", method="stream"):
    for youtube_channel in channels():
        youtube_channel_url = "https://www.youtube.com/{}/videos".format(youtube_channel)
        print("Preparing channel {}".format(youtube_channel))

        command = ['yt-dlp', '--compat-options', 'no-youtube-channel-redirect', '--print', 'channel_url', youtube_channel_url]
        process = subprocess.Popen(command, stdout = subprocess.PIPE)
        while True:
            line = process.stdout.readline()
            channel_id = line.decode("utf-8").rstrip().split('/')[-1]
            break
        process.kill()
        makecleanfolder("{}/{}".format(media_folder, "{} [{}]".format(youtube_channel,channel_id)))

        command = ['yt-dlp', '--compat-options', 'no-youtube-channel-redirect', '--print', '%(id)s;%(title)s', '--dateafter', 'today-60days', '--playlist-start', '1', '--playlist-end', '30', youtube_channel_url]
        process = subprocess.Popen(command, stdout = subprocess.PIPE)
        while True:
            try:
                line = process.stdout.readline()
                if not line:
                    break
                

                video_id = str(line.decode("utf-8")).rstrip().split(';')[0]
                video_name = "{} [{}]".format(str(line.decode("utf-8")).rstrip().split(';')[1], video_id)
                file_content = "{}:{}/{}/{}/{}".format(host, port, platform, method, video_id)
                file_path = "{}/{}/{}.{}".format(media_folder, "{} [{}]".format(youtube_channel,channel_id), video_name, "strm")

                data = {
                    "video_id" : video_id, 
                    "video_name" : video_name
                }
                if not os.path.isfile(file_path):
                    createSTRM(file_path, file_content)

                print(data)
            except:
                break
            

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
