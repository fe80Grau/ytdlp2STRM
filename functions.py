import json
import glob
import os

#Reading config file
with open('./config/config.json', 'r') as f:
    config = json.load(f)


host = config["ytdlp2strm_host"]
port = config["ytdlp2strm_port"]


def make_clean_folder(folder):
    print("Clearing {} folder...".format(folder))
    try:
        if(os.path.isdir(folder)):
            if not config['ytdlp2strm_keep_old_strm']:
                items = glob.glob(  "{}/*".format(glob.escape(folder)) )
                for r in items:
                    os.remove(r)
        else:
            os.mkdir(folder)
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
