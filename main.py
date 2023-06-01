from flask import Flask, stream_with_context, request, Response, send_from_directory, send_file, redirect
from threading import Thread
import subprocess
import time
import json
import urllib.request
import urllib.error
import os
app = Flask(__name__)
import config.routes


#Reading config file
with open('./config/config.json', 'r') as f:
    config = json.load(f)
    
keep_downloaded = 1800 #in seconds

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


if __name__ == "__main__":
    #Thread for clean_old_videos
    thread = Thread(target=clean_old_videos)
    #Set as daemon to keep run behavior sync with main thread (by default)
    thread.daemon = True
    thread.start()
    #Run Flask server
    app.run(host='0.0.0.0',port=config['ytdlp2strm_port'])
