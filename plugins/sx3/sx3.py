from flask import stream_with_context, Response, redirect
from sanitize_filename import sanitize
import os
import json
import time
import subprocess
import requests
from bs4 import BeautifulSoup
from clases.config import config as c
from clases.worker import worker as w
from clases.folders import folders as f
from clases.nfo import nfo as n

## -- SX3 CLASS
class Sx3:
    def __init__(self, channel=False):
        self.channel = channel
        self.channel_folder = self.channel.split('/')[-2]
        self.id = self.get_id()
        self.api_data = self.get_api_response_data()
        self.name = self.api_data['resposta']['items']['item'][0]['programes_tv'][0]['titol']
        self.description = self.api_data['resposta']['items']['item'][0]['programes_tv'][0]['desc']
        self.poster = self.get_images()['poster']
        self.landscape = self.get_images()['landscape']
        

    def get_api_response_data(self):
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}
        api_serie = "https://api.ccma.cat/videos?version=2.0&_format=json&items_pagina=5000&tipus_contingut=PPD&ordre=capitol&idioma=PU_CATALA&programatv_id={}&perfil=default".format(self.id)
        api_serie_response = requests.get(api_serie, headers=headers)
        api_serie_response_data = json.loads(api_serie_response.text)

        return api_serie_response_data

    def get_id(self):
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}
        page = requests.get(self.channel, headers=headers)
        #print(page.content)
        soup = BeautifulSoup(page.content, 'html.parser')
        element = soup.find('div', {'class': 'titolMedia'}).find('a')
        first_episode_id = element['href']
        first_episode_id = first_episode_id.strip('/').split('/')[-1]

        #get serie id from first_episode_id
        api_video = "https://api-media.ccma.cat/pvideo/media.jsp?media=video&versio=vast&idint={}&profile=pc&producte=sx3&broadcast=false&format=dm".format(first_episode_id)
        api_video_response = requests.get(api_video, headers=headers)
        api_video_response_data = json.loads(api_video_response.text)
        serie_id = api_video_response_data['informacio']['programa_id']

        return serie_id

    def get_images(self):
        for image in self.api_data['resposta']['items']['item'][0]['programes_tv'][0]['imatges']:
            if image['mida'] == "320x466":
                poster = image['text']
            if image['mida'] == "1600x284":
                landscape = image['text']

        return {
            "poster" : poster,
            "landscape" : landscape
        }
## -- END


## -- LOAD CONFIG AND CHANNELS FILES
ytdlp2strm_config = c.config(
    './config/config.json'
).get_config()

config = c.config(
    './plugins/sx3/config.json'
).get_config()

channels = c.config(
    config["channels_list_file"]
).get_channels()

source_platform = "sx3"
media_folder = config["strm_output_folder"]
channels_list = config["channels_list_file"]
## -- END

## -- MANDATORY TO_STRM FUNCTION 
def to_strm(method):
    for channel in channels:
        try:
            #Clearing channel folder name
            sx3 = Sx3(channel)
            #Make a folder and inflate nfo file
            f.folders().make_clean_folder(
                "{}/{}".format(
                    media_folder,
                    sanitize(
                        "{}".format(
                            sx3.channel_folder
                        )
                    )
                ),
                True,
                config
            )

            ## -- BUILD CHANNEL NFO FILE
            n.nfo(
                "tvshow",
                "{}/{}".format(
                    media_folder, 
                    "{}".format(
                        sx3.channel_folder,
                    )
                ),
                {
                    "title" : sx3.name,
                    "plot" : sx3.description,
                    "season" : "1",
                    "episode" : "-1",
                    "landscape" : sx3.landscape,
                    "poster" : sx3.poster,
                    "studio" : "SX3"
                }
            ).make_nfo()
            ## -- END 

            ## -- BUILD STRM
            last_capitol = False
            capitols = []
            for item in sx3.api_data['resposta']['items']['item']:
                #get serie id from first_episode_id
                item['capitol_temporada'] = str(item['capitol_temporada']).zfill(2)
                item['titol'] = item['titol'].split('-')
                if len(item['titol']) > 1:
                    item['titol'] = item['titol'][1]
                else:
                    item['titol'] = item['titol'][0]

                if 'temporades' in item:
                    temporada = item['temporades'][0]['desc']
                else:
                    if last_capitol:
                        if 'temporada' in last_capitol:
                            temporada = last_capitol['temporada']
                        else:
                            temporada = False

                capitol = {
                    "capitol" : item['capitol'],
                    "temporada": temporada,
                    "capitol_temporada": item['capitol_temporada'],
                    "titol": item['titol'],
                    "id": item['id'],
                    "id_serie": sx3.id,
                }
                capitols.append(capitol)

                last_capitol = capitol

                try:
                    sn = ''.join([n for n in temporada if n.isdigit()])[0]
                except:
                    sn = 0

                sn = str(sn).zfill(2)
                
                video_name = "{} - {}".format(
                    "S{}E{}".format(
                        sn, 
                        item['capitol_temporada']
                    ), 
                    item['titol']
                )
                url = "{}_{}".format(item['id'], sx3.id)

                file_content = "http://{}:{}/{}/{}/{}".format(
                    ytdlp2strm_config['ytdlp2strm_host'], 
                    ytdlp2strm_config['ytdlp2strm_port'], 
                    source_platform, 
                    method, 
                    url
                )
                file_path = "{}/{}/{}/{}.{}".format(
                    media_folder,  
                    sanitize(
                        "{}".format(
                            sx3.channel_folder
                        )
                    ),  
                    sanitize(
                        "S{} - {}".format(
                            sn,
                            temporada
                        )
                    ), 
                    sanitize(
                        video_name
                    ), 
                    "strm"
                )
                f.folders().make_clean_folder(
                    "{}/{}/{}".format(
                        media_folder,  
                        sanitize(
                            "{}".format(
                                sx3.channel_folder
                            )
                        ),  
                        sanitize(
                            "S{} - {}".format(
                                sn, 
                                temporada
                            )
                        )
                    ),
                    False,
                    config
                )

                if not os.path.isfile(file_path):
                    f.folders().write_file(file_path, file_content)
        except:
            continue
        ## -- END
## -- END

## -- EXTRACT / REDIRECT VIDEO DATA 
def direct(sx3_id): 
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}
    api_video = "https://api-media.ccma.cat/pvideo/media.jsp?media=video&versio=vast&idint={}&profile=pc&producte=sx3&broadcast=false&format=dm".format(sx3_id.split('_')[0])
    
    
    api_video_response = requests.get(api_video, headers=headers)    
    api_video_response_data = json.loads(api_video_response.text)
    mpd_url = api_video_response_data['media']['url'][0]['file']
    urls = api_video_response_data['media']['url']
    for url in urls:
        if url['label'] == "720p":
            mpd_url = url["file"]
    if config['http_get_proxy']:
        mpd_url = "{}{}".format(config['http_get_proxy_url'], mpd_url)
        
    return redirect(mpd_url, code=301)

def bridge(sx3_id):
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}
    api_video = "https://api-media.ccma.cat/pvideo/media.jsp?media=video&versio=vast&idint={}&profile=pc&producte=sx3&broadcast=false&format=dm".format(sx3_id.split('_')[0])
    
    api_video_response = requests.get(api_video, headers=headers)    
    api_video_response_data = json.loads(api_video_response.text)
    mpd_url = api_video_response_data['media']['url'][0]['file']
    urls = api_video_response_data['media']['url']
    for url in urls:
        if url['label'] == "720p":
            mpd_url = url["file"]
    v_headers = {}
    if not config['proxy']:
        v_headers = requests.head(mpd_url).headers.items()
    else:
        v_headers = requests.head(mpd_url,
            headers=headers, 
            proxies=dict(
                http=config['proxy_url'],
                https=config['proxy_url']
            )
        ).headers.items()

    def generate():
        startTime = time.time()
        buffer = []
        sentBurst = False

        if not config['proxy']:
            command = ["ffmpeg", "-i", mpd_url, "-codec", "copy", "-movflags", "frag_keyframe+faststart", "-f", "mp4", "-"]
        else:
            command = ["ffmpeg", "-i", mpd_url, "-vcodec", "copy", "-movflags", "frag_keyframe+faststart", "-f", "mp4", "-http_proxy", config['proxy_url'], "-"]


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
                        #print("Send initial burst #", i)
                        yield buffer.pop(0)

                elif time.time() > startTime + 3 and len(buffer) > 0:
                    yield buffer.pop(0)

                process.poll()
                if isinstance(process.returncode, int):
                    if process.returncode > 0:
                        print('ffmpeg Error', process.returncode)
                    break
        finally:
            process.kill()

    print(v_headers)
    return Response(stream_with_context(generate()), mimetype = "video/mp4") 

def download(sx3_id):
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}
    api_video = "https://api-media.ccma.cat/pvideo/media.jsp?media=video&versio=vast&idint={}&profile=pc&producte=sx3&broadcast=false&format=dm".format(sx3_id.split('_')[0])
    
    api_video_response = requests.get(api_video, headers=headers)    
    api_video_response_data = json.loads(api_video_response.text)
    #print(api_video)
    mpd_url = api_video_response_data['media']['url'][0]['file']
    urls = api_video_response_data['media']['url']
    for url in urls:
        if url['label'] == "720p":
            mpd_url = url["file"]

    if not config['proxy']:
        req = requests.get(mpd_url, stream = True)
    else:
        req = requests.get(
            mpd_url, 
            headers=headers, 
            proxies=dict(
                http=config['proxy_url'],
                https=config['proxy_url']
            )
        )

    return Response(stream_with_context(req.iter_content(chunk_size=1024)), content_type = req.headers['content-type'])
## -- END