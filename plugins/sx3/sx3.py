from flask import Flask, stream_with_context, request, Response, send_from_directory, send_file, redirect
from functions import make_clean_folder, write_file, tvinfo_scheme, host, port
from sanitize_filename import sanitize
import os
import json
import time
import platform
import subprocess
import fnmatch
import xml.etree.ElementTree as ET
import requests
from isodate import parse_duration
from bs4 import BeautifulSoup

source_platform = "sx3"
#Reading config file
config_file = './plugins/sx3/config.json'
if not os.path.isfile(config_file):
    print("No config.json detected, using config.example.json. Please check this in current plugin folder")
    config_file = './plugins/sx3/config.example.json'

with open(
        config_file, 
        'r'
    ) as f:
    config = json.load(f)

media_folder = config["strm_output_folder"]
channels_list = config["channels_list_file"]

def channels():
    channels_list_local = channels_list

    if not os.path.isfile(channels_list_local):
        print("No channel_list.json detected, using channel_list.example.json. Please check this in current plugin folder")
        channels_list_local = './plugins/sx3/channel_list.example.json'

    with open(
            channels_list_local, 
            'r'
        ) as f:
        channels = json.load(f)
    return channels

def get_bitrate_from_mpd(mpd_data):
    root = ET.fromstring(mpd_data)
    representations = root.findall('Representation')
    
    bitrates = []
    
    for rep in representations:
        print("Test")
        bitrate = int(rep.attrib.get('bandwidth'))
        bitrates.append(bitrate)
    
    return bitrates

def parse_duration_from_mpd(mpd_data):
    root = ET.fromstring(mpd_data)
    duration_str = root.attrib.get("mediaPresentationDuration")
    duration = parse_duration(duration_str).total_seconds()
    return duration

def to_nfo(params):
    #api_serie_response_data from to_strm function
    channel_name = params['data']['resposta']['items']['item'][0]['programes_tv'][0]['titol']
    description = params['data']['resposta']['items']['item'][0]['programes_tv'][0]['desc']
    images = params['data']['resposta']['items']['item'][0]['programes_tv'][0]['imatges']
    poster = params['data']['resposta']['items']['item'][0]['programes_tv'][0]['imatges'][0]['text']
    landscape = params['data']['resposta']['items']['item'][0]['programes_tv'][0]['imatges'][0]['text']
    preview = params['data']['resposta']['items']['item'][0]['programes_tv'][0]['imatges'][0]['text']

    for image in images:
        if image['mida'] == "320x466":
            poster = image['text']
        if image['mida'] == "1600x284":
            landscape = image['text']
        if image['mida'] == "320x466":
            preview = image['text']

    output_nfo = tvinfo_scheme().format(
        channel_name,
        channel_name,
        channel_name,
        description,
        landscape, landscape,
        poster, poster,
        preview, preview,
        "-",
        "SX3",
        "SX3"
    )

    
    if params['sx3_channel_folder']:
        file_path = "{}/{}/{}.{}".format(media_folder, "{}".format(params['sx3_channel_folder']), "tvshow", "nfo")
        write_file(file_path, output_nfo)

def to_strm(method):
    for channel in channels():
        #Clearing channel folder name
        sx3_channel_folder = channel.split('/')[-2]
        #Make a folder and inflate nfo file
        make_clean_folder(
            "{}/{}".format(
                media_folder,
                sanitize(
                    "{}".format(
                        sx3_channel_folder
                    )
                )
            )
        )

        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}
        page = requests.get(channel, headers=headers)
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

        api_serie = "https://api.ccma.cat/videos?version=2.0&_format=json&items_pagina=5000&tipus_contingut=PPD&ordre=capitol&idioma=PU_CATALA&programatv_id={}&perfil=default".format(serie_id)
        
        api_serie_response = requests.get(api_serie, headers=headers)
        api_serie_response_data = json.loads(api_serie_response.text)

        to_nfo(
            {
                'data' : api_serie_response_data,
                'sx3_channel_folder' : sanitize(
                    "{}".format(
                        sx3_channel_folder
                    )
                )
            }
        )
        
        #print(api_serie)

        
        last_capitol = False
        capitols = []
        for item in api_serie_response_data['resposta']['items']['item']:
            #get serie id from first_episode_id


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
                "id_serie": serie_id,
            }
            print(capitol)
            capitols.append(capitol)

            last_capitol = capitol

            #print(capitol)
            try:
                sn = ''.join([n for n in temporada if n.isdigit()])[0]
            except:
                sn = 0

            video_name = "{} - {}".format("S{}E{}".format(sn, item['capitol_temporada']), item['titol'])
            url = "{}_{}".format(item['id'], serie_id)

            file_content = "http://{}:{}/{}/{}/{}".format(host, port, source_platform, method, url)
            file_path = "{}/{}/{}/{}.{}".format(media_folder,  sanitize("{}".format(sx3_channel_folder)),  sanitize("S{} - {}".format(sn, temporada)), sanitize(video_name), "strm")
            make_clean_folder("{}/{}/{}".format(media_folder,  sanitize("{}".format(sx3_channel_folder)),  sanitize("S{} - {}".format(sn, temporada))))
            data = {
                "video_name" : video_name
            }
            if not os.path.isfile(file_path):
                write_file(file_path, file_content)

                
def direct(sx3_id): #Sponsorblock doesn't work in this mode
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
    #print(mpd_url)
    return redirect(mpd_url, code=301)

def bridge(sx3_id):
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
