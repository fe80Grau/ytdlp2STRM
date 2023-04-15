from flask import Flask, stream_with_context, request, Response, send_from_directory, send_file
from threading import Thread
import subprocess
import time
import json
import urllib.request
import urllib.error
import os
app = Flask(__name__)



#Reading config file
with open('config.json', 'r') as f:
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
            
        

### YOUTUBE ZONE
#Stream data directly throught http (no serve video duration info, no disk usage)
@app.route("/youtube/stream/<youtube_id>")
def youtube(youtube_id):
    print(request.headers)
    print(request.cookies)
    print(request.data)
    print(request.args)
    print(request.form)
    print(request.endpoint)
    print(request.method)
    print(request.remote_addr)
    def generate():
        startTime = time.time()
        buffer = []
        sentBurst = False

        ytdlp_command = ['yt-dlp', '-o', '-', '-f', 'bv*+ba+ba.2', '--audio-multistreams', youtube_id]
        process = subprocess.Popen(ytdlp_command, stdout=subprocess.PIPE)
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

#Download video and semd data throught http (serve video duration info, disk usage **clean_old_videos fucntion save your money)
@app.route("/youtube/download/<youtube_id>")
def youtube_full(youtube_id):
    ytdlp_command = ['yt-dlp', '-f', 'bv*+ba+ba.2', '--force-keyframes', '--sponsorblock-remove', 'sponsor', '--restrict-filenames', youtube_id]
    print(ytdlp_command)
    process = subprocess.call(ytdlp_command)
    filename = subprocess.getoutput("yt-dlp --print filename --restrict-filenames {}".format(youtube_id))
    return send_file(filename)


### CRUNCHUROLL ZONE
### under construction...

if __name__ == "__main__":
    #Thread for clean_old_videos
    thread = Thread(target=clean_old_videos)
    #Set as daemon to keep run behavior sync with main thread (by default)
    thread.daemon = True
    thread.start()
    #Run Flask server
    app.run(host='0.0.0.0',port=config['ytdlp2strm_port'])
