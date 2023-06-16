import json
import glob
import os
import time

#Reading config file
config_file = './config/config.json'
if not os.path.isfile(config_file):
    print("No config.json detected, using config.example.json. Please check this in config folder")
    config_file = './config/config.example.json'

with open(config_file, 'r') as f:
    config = json.load(f)


host = config["ytdlp2strm_host"]
port = config["ytdlp2strm_port"]
keep_downloaded = 1800 #in seconds for clean_old_videos function


def make_clean_folder(folder):
    #print("Cleaning {} folder...".format(folder))
    try:
        if(os.path.isdir(folder)):
            if not config['ytdlp2strm_keep_old_strm']:
                items = glob.glob(  "{}/*".format(glob.escape(folder)) )
                for r in items:
                    os.remove(r)
        else:
            os.makedirs(folder)
    except Exception as e:
        print(e)
        return False
    return True

def write_file(file, content):
    try:
        f = open(file, "w")
        f.write(content)
        f.close()
    except Exception as e:
        print(e)
        return False
    return True

def tvinfo_scheme():
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

    return tvinfo_scheme


#Function used in thread to remove files webm older than **keep_downloaded** 
def clean_old_videos():
    while True:
        try:
            time.sleep(60)
            path = os.getcwd()
            now = time.time()
            for f in os.listdir(path):
                extension = f.split('.')[-1]
                if extension == "webm" and os.stat(f).st_ctime < now - keep_downloaded:
                    if os.path.isfile(f):
                        os.remove(os.path.join(path, f))
        except:
            continue