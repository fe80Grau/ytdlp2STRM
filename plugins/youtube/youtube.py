import os
import json
import time
import platform
import subprocess
import requests
import html
import re
from datetime import datetime

from clases.config import config as c
from clases.worker import worker as w
from clases.folders import folders as f
from clases.nfo import nfo as n
from clases.log import log as l

from sanitize_filename import sanitize
from flask import stream_with_context, Response, send_file, redirect, abort, request

## -- LOAD CONFIG AND CHANNELS FILES
ytdlp2strm_config = c.config(
    './config/config.json'
).get_config()

config = c.config(
    './plugins/youtube/config.json'
).get_config()

channels = c.config(
    config["channels_list_file"]
).get_channels()

media_folder = config["strm_output_folder"]
days_dateafter = config["days_dateafter"]
videos_limit = config["videos_limit"]
try:
    cookies = config["cookies"]
    cookie_value = config["cookie_value"]
except:
    cookies = 'cookies-from-browser'
    cookie_value = 'chrome'

source_platform = "youtube"
host = ytdlp2strm_config['ytdlp2strm_host']
port = ytdlp2strm_config['ytdlp2strm_port']

SECRET_KEY = os.environ.get('AM_I_IN_A_DOCKER_CONTAINER', False)
DOCKER_PORT = os.environ.get('DOCKER_PORT', False)
if SECRET_KEY:
    port = DOCKER_PORT

if 'proxy' in config:
    proxy = config['proxy']
    proxy_url = config['proxy_url']
else:
    proxy = False
    proxy_url = ""

## -- END

class Youtube:
    def __init__(self, channel=None):
        self.channel = channel
        self.channel_url = None
        self.channel_name = None
        self.channel_description = None
        self.channel_poster = None
        self.channel_landscape = None
    
    def get_results(self):
        if 'extractaudio-' in self.channel:
            islist = False
            self.channel_url = self.channel.replace(
                'extractaudio-',
                ''
            )
            if 'list-' in self.channel:
                islist = True
                self.channel_url = self.channel.replace(
                    'list-',
                    ''
                )
                if not 'www.youtube' in self.channel_url:
                    self.channel_url = f'https://www.youtube.com/playlist?list={self.channel_url}'
            else:
                if not 'www.youtube' in self.channel_url:
                    self.channel_url = f'https://www.youtube.com/{self.channel_url}'


            self.channel_name = self.get_channel_name()
            self.channel_description = self.get_channel_description() if not islist else  f'Playlist {self.channel_name}'
            thumbs = self.get_channel_images()
            self.channel_poster = thumbs['poster']
            self.channel_landscape = thumbs['landscape']

            return self.get_channel_audios() if not islist else  self.get_list_audios()
        
        elif 'keyword' in self.channel:
            return self.get_keyword_videos()
        
        elif 'list' in self.channel:
            self.channel_url = self.channel.replace(
                'list-',
                ''
            )
            if not 'www.youtube' in self.channel_url:
                self.channel_url = f'https://www.youtube.com/playlist?list={self.channel_url}'

            self.channel_name = self.get_channel_name()
            self.channel_description = f'Playlist {self.channel_name}'
            thumbs = self.get_channel_images()
            self.channel_poster = thumbs['poster']
            self.channel_landscape = thumbs['landscape']
            return self.get_list_videos()

        else:
            self.channel_url = self.channel
            if not 'www.youtube' in self.channel:
                self.channel_url = f'https://www.youtube.com/{self.channel}'

            self.channel_name = self.get_channel_name()
            self.channel_description = self.get_channel_description()
            thumbs = self.get_channel_images()
            self.channel_poster = thumbs['poster']
            self.channel_landscape = thumbs['landscape']
            return self.get_channel_videos()
    
    def get_list_videos(self):
        command = [
            'yt-dlp', 
            '--compat-options', 'no-youtube-channel-redirect',
            '--compat-options', 'no-youtube-unavailable-videos',
            '--playlist-start', '1', 
            '--playlist-end', str(videos_limit), 
            '--no-warning',
            '--dump-json',
            self.channel_url
        ]
        result = w.worker(command).output()
        result = subprocess.run(command, capture_output=True, text=True)
        videos = []
        for line in result.stdout.split('\n'):
            if line.strip():
                data = json.loads(line)
                
                video = {
                    'id': data.get('id'),
                    'title': data.get('title'),
                    'upload_date': data.get('upload_date'),
                    'thumbnail': data.get('thumbnail'),
                    'description': data.get('description'),
                    'channel_id': self.channel_url.split('list=')[1],
                    'uploader_id': sanitize(self.channel_name)
                }
                videos.append(video)
        
        return videos
    
    def get_keyword_videos(self):
        keyword = self.channel.split('-')[1]
        command = [
            'yt-dlp', 
            '-f', 'best', 'ytsearch10:["{}"]'.format(keyword),
            '--compat-options', 'no-youtube-channel-redirect',
            '--compat-options', 'no-youtube-unavailable-videos',
            '--playlist-start', '1', 
            '--playlist-end', videos_limit, 
            '--no-warning',
            '--dump-json'
        ]

        if config['days_dateafter'] == "0":
            command.pop(8)
            command.pop(8)

        result = w.worker(command).output()
        result = subprocess.run(command, capture_output=True, text=True)
        videos = []
        for line in result.stdout.split('\n'):
            if line.strip():
                data = json.loads(line)
                
                video = {
                    'id': data.get('id'),
                    'title': data.get('title'),
                    'upload_date': data.get('upload_date'),
                    'thumbnail': data.get('thumbnail'),
                    'description': data.get('description'),
                    'channel_id': data.get('channel_id'),
                    'uploader_id': data.get('uploader_id')
                }
                videos.append(video)
        
        return videos
    
    def get_keyword_audios(self):
        keyword = self.channel.split('-')[1]
        command = [
            'yt-dlp', 
            '-f', 'best', 'ytsearch10:["{}"]'.format(keyword),
            '--compat-options', 'no-youtube-channel-redirect',
            '--compat-options', 'no-youtube-unavailable-videos',
            '--playlist-start', '1', 
            '--playlist-end', videos_limit, 
            '--no-warning',
            '--dump-json'
        ]

        if config['days_dateafter'] == "0":
            command.pop(8)
            command.pop(8)

        result = w.worker(command).output()
        result = subprocess.run(command, capture_output=True, text=True)
        videos = []
        for line in result.stdout.split('\n'):
            if line.strip():
                data = json.loads(line)
                
                video = {
                    'id': f'{data.get('id')}-audio',
                    'title': data.get('title'),
                    'upload_date': data.get('upload_date'),
                    'thumbnail': data.get('thumbnail'),
                    'description': data.get('description'),
                    'channel_id': data.get('channel_id'),
                    'uploader_id': data.get('uploader_id')
                }
                videos.append(video)
        
        return videos
    
    def get_channel_audios(self):
        cu = self.channel

        if not '/streams' in self.channel:
            cu = f'{self.channel_url}/videos'

        command = [
            'yt-dlp', 
            '--compat-options', 'no-youtube-channel-redirect',
            '--compat-options', 'no-youtube-unavailable-videos',
            '--dateafter', f"today-{days_dateafter}days", 
            '--playlist-start', '1', 
            '--playlist-end', str(videos_limit), 
            '--no-warning',
            '--dump-json',
            f'{cu}'
        ]


        result = w.worker(command).output()
        result = subprocess.run(command, capture_output=True, text=True)
        # Procesa la salida JSON
        videos = []
        for line in result.stdout.split('\n'):
            if line.strip():
                data = json.loads(line)
                video = {
                    'id': f'{data.get('id')}-audio',
                    'title': data.get('title'),
                    'upload_date': data.get('upload_date'),
                    'thumbnail': data.get('thumbnail'),
                    'description': data.get('description'),
                    'channel_id': data.get('channel_id'),
                    'uploader_id': data.get('uploader_id')
                }
                videos.append(video)
        
        return videos
    
    def get_list_audios(self):
        command = [
            'yt-dlp', 
            '--compat-options', 'no-youtube-channel-redirect',
            '--compat-options', 'no-youtube-unavailable-videos',
            '--playlist-start', '1', 
            '--playlist-end', str(videos_limit), 
            '--no-warning',
            '--dump-json',
            self.channel_url
        ]
        result = w.worker(command).output()
        result = subprocess.run(command, capture_output=True, text=True)
        videos = []
        for line in result.stdout.split('\n'):
            if line.strip():
                data = json.loads(line)
                
                video = {
                    'id': f'{data.get('id')}-audio',
                    'title': data.get('title'),
                    'upload_date': data.get('upload_date'),
                    'thumbnail': data.get('thumbnail'),
                    'description': data.get('description'),
                    'channel_id': self.channel_url.split('list=')[1],
                    'uploader_id': sanitize(self.channel_name)
                }
                videos.append(video)
        
        return videos
    
    def get_channel_videos(self):
        cu = self.channel

        if not '/streams' in self.channel:
            cu = f'{self.channel}/videos'
            

        command = [
            'yt-dlp', 
            '--compat-options', 'no-youtube-channel-redirect',
            '--compat-options', 'no-youtube-unavailable-videos',
            '--dateafter', f"today-{days_dateafter}days", 
            '--playlist-start', '1', 
            '--playlist-end', str(videos_limit), 
            '--no-warning',
            '--dump-json',
            f'{cu}'
        ]
        result = w.worker(command).output()
        result = subprocess.run(command, capture_output=True, text=True)
        # Procesa la salida JSON
        videos = []
        for line in result.stdout.split('\n'):
            if line.strip():
                data = json.loads(line)
                
                video = {
                    'id': data.get('id'),
                    'title': data.get('title'),
                    'upload_date': data.get('upload_date'),
                    'thumbnail': data.get('thumbnail'),
                    'description': data.get('description'),
                    'channel_id': data.get('channel_id'),
                    'uploader_id': data.get('uploader_id')
                }
                videos.append(video)
        
        return videos

    def get_channel_name(self):
        #get channel or playlist name
        if 'playlist' in self.channel_url:
            command = ['yt-dlp', 
                    '--compat-options', 'no-youtube-unavailable-videos',
                    '--print', '"%(playlist_title)s"', 
                    '--playlist-items', '1',
                    '--restrict-filenames',
                    '--ignore-errors',
                    '--no-warnings',
                    '--compat-options', 'no-youtube-channel-redirect',
                    '--no-warnings',
                    f'{self.channel_url}'
            ]
        else:
            command = ['yt-dlp', 
                        '--compat-options', 'no-youtube-unavailable-videos',
                        '--print', '"%(channel)s"',
                        '--restrict-filenames',
                        '--ignore-errors',
                        '--no-warnings',
                        '--playlist-items', '1',
                        '--compat-options', 'no-youtube-channel-redirect',
                        f'{self.channel_url}'
            ]
        self.set_proxy(command)
        self.channel_name = w.worker(command).output()
        return sanitize(
            self.channel_name
        )
    
    def get_channel_description(self):
        #get description
        if platform.system() == "Linux":
            command = [
                'yt-dlp', 
                self.channel_url, 
                '--write-description', 
                '--playlist-items', '0',
                '--output', '"{}/{}.description"'.format(
                    media_folder, 
                    sanitize(self.channel_name)
                )
            ]
            self.set_proxy(command)
            command = (
                command 
                + [
                    '>', 
                    '/dev/null', 
                    '2>&1',
                    '&&', 
                    'cat', 
                    '"{}/{}.description"'.format(
                        media_folder, 
                        sanitize(
                            self.channel_name
                        )
                    )
                ]
            )
            

            self.channel_description = w.worker(command).output()
            try:
                os.remove("{}/{}.description".format(media_folder,sanitize(self.channel_name)))
            except:
                pass
        else:
            command = [
                'yt-dlp', 
                '--write-description', 
                '--playlist-items', '0',
                '--output', '"{}/{}.description"'.format(
                    media_folder, 
                    sanitize(
                        self.channel_name
                    )
                ),
                self.channel_url, 
            ]
            self.set_proxy(command)
            command = (
                command 
                + [
                    '>', 
                    'nul', 
                    '2>&1', 
                    '&&', 
                    'more', 
                    '"{}/{}.description"'.format(
                        media_folder,
                        sanitize(
                            self.channel_name
                        )
                    )
                ]
            )

            try:
                self.channel_description = w.worker(command).output()
            except:
                d_file = open(
                    "{}/{}.description".format(
                        media_folder,
                        sanitize(
                            self.channel_name
                        )
                    ),
                    'r',
                    encoding='utf-8'
                )

                self.channel_description = d_file.read()
                d_file.close()

            try:
                os.remove(
                    "{}/{}.description".format(
                        media_folder,
                        sanitize(
                            self.channel_name
                        )
                    )
                )
            except:
                pass

        return self.channel_description
    
    def get_channel_images(self):
        c = 0
        command = ['yt-dlp', 
                    '--list-thumbnails',
                    '--restrict-filenames',
                    '--ignore-errors',
                    '--no-warnings',
                    '--playlist-items', '0',
                    self.channel_url
        ]
        self.set_proxy(command)
        landscape = None
        poster = None
        try:
            lines = (
                w.worker(
                    command
                ).output()
                .split('\n')
            )

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

            poster = ""
            try:
                url_avatar_uncropped_index = next(
                    (index for (index, d) in enumerate(thumbnails) if d["ID"] == "avatar_uncropped"), 
                    None
                )
                poster = thumbnails[url_avatar_uncropped_index]['URL']
            except:
                pass

            landscape = ""
            try:
                url_max_landscape_index = next(
                    (index for (index, d) in enumerate(thumbnails) if d["ID"] == "banner_uncropped"), 
                    None
                )

                landscape = thumbnails[url_max_landscape_index-1]['URL']
            except:
                pass
        except:
            pass

        return {
            "landscape" : landscape,
            "poster" : poster
        }

    def set_proxy(self, command):
        if proxy:
            if proxy_url != "":
                command.append('--proxy')
                command.append(proxy_url)
    
    def set_cookies(self, command):
        command.append(f'--{cookies}')
        command.append(cookie_value)

def filter_and_modify_bandwidth(m3u8_content):
    lines = m3u8_content.splitlines()
    
    highest_bandwidth = 0
    best_video_info = None
    best_video_url = None
    media_lines = []
    
    high_audio = False
    sd_audio = ""
    for i in range(len(lines)):
        line = lines[i]
        if line.startswith("#EXT-X-STREAM-INF:"):
            info = line
            url = lines[i + 1]
            bandwidth = int(info.split("BANDWIDTH=")[1].split(",")[0])

            if bandwidth > highest_bandwidth:
                highest_bandwidth = bandwidth
                best_video_info = info.replace(f"BANDWIDTH={bandwidth}", "BANDWIDTH=279001")
                best_video_url = url
        
        if line.startswith("#EXT-X-MEDIA:URI"):
            if '234' in line:
                high_audio = True
                media_lines.append(line)
            else:
                sd_audio = line

    if not high_audio:
        media_lines.append(sd_audio)

    # Create the final M3U8 content
    final_m3u8 = "#EXTM3U\n#EXT-X-INDEPENDENT-SEGMENTS\n"
    
    # Add all EXT-X-MEDIA lines
    for media_line in media_lines:
        final_m3u8 += f"{media_line}\n"

    if best_video_info:
        final_m3u8 += f"{best_video_info}\n{best_video_url}\n"

    return final_m3u8

def clean_text(text):
    # Reemplazar los caracteres especiales habituales y eliminar los que no son necesarios

    # Escapando caracteres que deben mantenerse pero asegurándote de que sean seguros
    text = html.escape(text)
    
    # Eliminar cualquier carácter no deseado usando expresiones regulares
    text = re.sub(r'[^\w\s\[\]\(\)\-\_\'\"\/\.\:\;\,]', '', text)
    
    return text

def to_strm(method):
    for youtube_channel in channels:
        yt = Youtube(youtube_channel)
        log_text = (" --------------- ")
        l.log("youtube", log_text)
        log_text = (f'Working {youtube_channel}...')
        l.log("youtube", log_text)
        videos = yt.get_results()
        channel_name = yt.channel_name
        channel_url = yt.channel_url
        channel_description = yt.channel_description

        log_text = (f'Channel URL: {channel_url}')
        l.log("youtube", log_text)
        log_text = (f'Channel Name: {channel_name}')
        l.log("youtube", log_text)
        log_text = (f'Channel Poster: {yt.channel_poster}')
        l.log("youtube", log_text)
        log_text = (f'Channel Landscape: {yt.channel_landscape}')
        l.log("youtube", log_text)
        log_text = ('Channel Description: ')
        l.log("youtube", log_text)
        log_text = (channel_description)
        l.log("youtube", log_text)
        
        if videos:
            log_text = (f'Videos detected: {len(videos)}')
            l.log("youtube", log_text)
            channel_nfo = False
            channel_folder = False
            for video in videos:
                video_id = video['id']
                channel_id = video['channel_id']
                video_name = video['title']
                thumbnail = video['thumbnail']
                description = video['description']
                date = datetime.strptime(video['upload_date'], '%Y%m%d')
                upload_date = date.strftime('%Y-%m-%d')
                year = date.year
                youtube_channel = video['uploader_id']
                youtube_channel_folder = youtube_channel.replace('/user/','@').replace('/streams','')
                file_content = f'http://{host}:{port}/{source_platform}/{method}/{video_id}'

                file_path = "{}/{}/{}.{}".format(
                    media_folder, 
                    sanitize(
                        "{} [{}]".format(
                            youtube_channel_folder,
                            channel_id
                        )
                    ),  
                    sanitize(video_name), 
                    "strm"
                )
                
                if not channel_folder:
                    f.folders().make_clean_folder(
                        "{}/{}".format(
                            media_folder,  
                            sanitize(
                                "{} [{}]".format(
                                    youtube_channel_folder,
                                    channel_id
                                )
                            )
                        ),
                        False,
                        ytdlp2strm_config
                    )
                    channel_folder = True

                if channel_url == None:
                    channel_url = f'https://www.youtube.com/channel/{channel_id}'
                    channel = Youtube(
                        channel_url
                    )
                    images = channel.get_channel_images()
                    channel.channel_url = channel_url
                    channel_name = channel.get_channel_name()
                    channel_description = channel.get_channel_description()
                    channel_landscape = images['landscape']
                    channel_poster = images['poster']
                else:
                    channel_landscape = yt.channel_landscape
                    channel_poster = yt.channel_poster

                ## -- BUILD CHANNEL NFO FILE
                if not channel_nfo:
                    n.nfo(
                        "tvshow",
                        "{}/{}".format(
                            media_folder, 
                            "{} [{}]".format(
                                youtube_channel,
                                channel_id
                            )
                        ),
                        {
                            "title" : youtube_channel,
                            "plot" : channel_description.replace('\n', ' <br/>'),
                            "season" : "1",
                            "episode" : "-1",
                            "landscape" : channel_landscape,
                            "poster" : channel_poster,
                            "studio" : "Youtube"
                        }
                    ).make_nfo()
                    channel_nfo = True
                ## -- END

                ## -- BUILD VIDEO NFO FILE
                n.nfo(
                    "episode",
                    "{}/{}".format(
                        media_folder, 
                        "{} [{}]".format(
                            youtube_channel,
                            channel_id
                        )
                    ),
                    {
                        "item_name" : sanitize(video_name),
                        "title" : sanitize(video_name),
                        "upload_date" : upload_date,
                        "year" : year,
                        "plot" : description.replace('\n', ' <br/>\n '),
                        "season" : "1",
                        "episode" : "",
                        "preview" : thumbnail
                    }
                ).make_nfo()
                ## -- END 

                if not os.path.isfile(file_path):
                    f.folders().write_file(
                        file_path, 
                        file_content
                    )
        else:
            log_text = (" no videos detected...") 
            l.log("youtube", log_text)

def direct(youtube_id, remote_addr):
    log_text = f'[{remote_addr}] Playing {youtube_id}'
    l.log("youtube", log_text)
    if not '-audio' in youtube_id:
        command = [
            'yt-dlp', 
            '-j',
            '--no-warnings',
            youtube_id
        ]
        Youtube().set_cookies(command)
        Youtube().set_proxy(command)
        full_info_json_str = w.worker(command).output()
        m3u8_url = None
        try:
            full_info_json = json.loads(full_info_json_str)

            for fmt in full_info_json["formats"]:
                if "manifest_url" in fmt.keys():
                    m3u8_url = fmt["manifest_url"]
                    break
        except:
            pass 

        if not m3u8_url:
            log_text = ('No manifest detected. Check your cookies config. \n* This video is age-restricted; some formats may be missing without authentication. Use --cookies-from-browser or --cookies for the authentication \n* Serving SD format. Please configure your cookies appropriately to access the manifest that serves the highest quality for this video')
            l.log("youtube", log_text)
            command = [
                'yt-dlp',
                '-f', 'best',
                '--get-url',
                '--no-warnings',
                f'{youtube_id}'
            ]
            Youtube().set_proxy(command)
            sd_url = w.worker(command).output()
            return redirect(sd_url.strip(), 301)
        else:
            response = requests.get(m3u8_url)
            if response.status_code == 200:
                m3u8_content = response.text
                filtered_content = filter_and_modify_bandwidth(m3u8_content)
                headers = {
                    'Content-Type': 'application/vnd.apple.mpegurl',
                    'Cache-Control': 'no-cache',
                    'Pragma': 'no-cache',
                    'Expires': '0'
                }
                
                return Response(filtered_content, mimetype='application/vnd.apple.mpegurl', headers=headers)
    else:
        s_youtube_id = youtube_id.split('-audio')[0]
        command = [
            'yt-dlp',
            '-f', 'bestaudio',
            '--get-url',
            '--no-warnings',
            f'{s_youtube_id}'
        ]
        Youtube().set_cookies(command)
        Youtube().set_proxy(command)
        audio_url = w.worker(command).output()
        return redirect(audio_url, 301)

    return "Manifest URL not found or failed to redirect.", 404

def bridge(youtube_id):
    s_youtube_id = youtube_id.split('-audio')[0]

    def generate():
        startTime = time.time()
        buffer = []
        sentBurst = False
        if config["sponsorblock"]:
            command = ['yt-dlp', '--no-warnings', '-o', '-', '-f', 'best', '--sponsorblock-remove',  config['sponsorblock_cats'], '--restrict-filenames', s_youtube_id]
        else:
            command = ['yt-dlp', '--no-warnings', '-o', '-', '-f', 'best', '--restrict-filenames', s_youtube_id]
        Youtube().set_proxy(command)
        if '-audio' in youtube_id:
            command[5] = 'bestaudio'
        

        #process = w.worker(command).pipe()
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        time.sleep(3)
        try:

            while True:
                # Get some data from ffmpeg
                #time.sleep(0.1)  # Espera brevemente por más datos
                line = process.stdout.read(1024)
                
                if not line:
                    break
                # We buffer everything before outputting it
                buffer.append(line)

                # Minimum buffer time, 3 seconds
                if sentBurst is False and time.time() > startTime + 3 and len(buffer) > 0:
                    sentBurst = True

                    for i in range(0, len(buffer) - 2):
                        yield buffer.pop(0)

                elif time.time() > startTime + 3 and len(buffer) > 0:
                    yield buffer.pop(0)

                process.poll()
        finally:
            process.kill()

    return Response(
        stream_with_context(generate()), 
        mimetype = "video/mp4"
    ) 

def download(youtube_id):
    s_youtube_id = youtube_id.split('-audio')[0]
    current_dir = os.getcwd()

    # Construyes la ruta hacia la carpeta 'temp' dentro del directorio actual
    temp_dir = os.path.join(current_dir, 'temp')
    if config["sponsorblock"]:
        command = ['yt-dlp', '-f', 'bv*+ba+ba.2', '-o',  os.path.join(temp_dir, '%(title)s.%(ext)s'), '--sponsorblock-remove',  config['sponsorblock_cats'], '--restrict-filenames', s_youtube_id]
    else:
        command = ['yt-dlp', '-f', 'bv*+ba+ba.2', '-o',  os.path.join(temp_dir, '%(title)s.%(ext)s'), '--restrict-filenames', s_youtube_id]
    Youtube().set_proxy(command)
    if '-audio' in youtube_id:
        command[2] = 'bestaudio'

    w.worker(command).call()
    filename = w.worker(
        ['yt-dlp', '--print', 'filename', '--restrict-filenames', "{}".format(youtube_id)]
    ).output()
    return send_file(
        os.path.join(temp_dir, filename)
    )