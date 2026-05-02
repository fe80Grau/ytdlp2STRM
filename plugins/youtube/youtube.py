import os
import json
import time
import platform
import subprocess
import requests
import html
import re
from datetime import datetime
from cachetools import TTLCache
from urllib.parse import quote
from utils.episode_numbering import format_episode_title
from utils.sanitize import sanitize
from flask import stream_with_context, Response, send_file, redirect, abort, request
from clases.config import config as c
from clases.worker import worker as w
from clases.folders import folders as f
from clases.nfo import nfo as n
from clases.log import log as l
from clases.jellyfin_notifier.jellyfin_notifier import JellyfinNotifier

recent_requests = TTLCache(maxsize=200, ttl=30)

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

try:
    lang = config["lang"]
except:
    lang = 'en'

try:
    episode_format = config["episode_format"]
except:
    episode_format = 'sequential'

try:
    download_subtitles = str(config["download_subtitles"]).lower() in ("true", "1", "yes", "on")
except:
    download_subtitles = False

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
                # Normalize URL - avoid double https://
                if self.channel_url.startswith('http'):
                    # Already a full URL, use as-is
                    pass
                elif not 'www.youtube' in self.channel_url:
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
            # Normalize URL - avoid double https://
            if self.channel.startswith('http'):
                # Already a full URL, use as-is
                self.channel_url = self.channel
            elif not 'www.youtube' in self.channel:
                self.channel_url = f'https://www.youtube.com/{self.channel}'
            else:
                self.channel_url = self.channel

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
        self.set_cookies(command)
        self.set_language(command)
        result = w.worker(command).output()
        videos = []
        for line in result.split('\n'):
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
            '-f', 'best', 'ytsearch:["{}"]'.format(keyword),
            '--compat-options', 'no-youtube-channel-redirect',
            '--compat-options', 'no-youtube-unavailable-videos',
            '--playlist-start', '1', 
            '--playlist-end', videos_limit, 
            '--no-warning',
            '--dump-json'
        ]
        self.set_cookies(command)
        self.set_language(command)

        if config['days_dateafter'] == "0":
            command.pop(8)
            command.pop(8)

        result = w.worker(command).output()
        videos = []
        for line in result.split('\n'):
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
        self.set_cookies(command)
        self.set_language(command)

        if config['days_dateafter'] == "0":
            command.pop(8)
            command.pop(8)

        result = w.worker(command).output()
        videos = []
        for line in result.split('\n'):
            if line.strip():
                data = json.loads(line)
                
                video = {
                    'id': f"{data.get('id')}-audio",
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
        self.set_cookies(command)
        self.set_language(command)

        result = w.worker(command).output()
        # Procesa la salida JSON
        videos = []
        for line in result.split('\n'):
            if line.strip():
                data = json.loads(line)
                video = {
                    'id': f"{data.get('id')}-audio",
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
        self.set_cookies(command)
        self.set_language(command)
        result = w.worker(command).output()
        videos = []
        for line in result.split('\n'):
            if line.strip():
                data = json.loads(line)
                
                video = {
                    'id': f"{data.get('id')}-audio",
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
        self.set_cookies(command)
        self.set_language(command)
        result = w.worker(command).output()
        # Procesa la salida JSON
        videos = []
        for line in result.split('\n'):
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
                    '--print', '%(playlist_title)s', 
                    '--playlist-items', '1',
                    '--restrict-filenames',
                    '--ignore-errors',
                    '--no-warnings',
                    '--compat-options', 'no-youtube-channel-redirect',
                    '--no-warnings',
                    f'{self.channel_url}'
            ]
        else:
            # Use uploader (friendly name) instead of channel (@-name)
            # First try to get uploader (friendly name)
            command = ['yt-dlp', 
                        '--compat-options', 'no-youtube-unavailable-videos',
                        '--print', '%(uploader)s',
                        '--restrict-filenames',
                        '--ignore-errors',
                        '--no-warnings',
                        '--playlist-items', '1',
                        '--compat-options', 'no-youtube-channel-redirect',
                        f'{self.channel_url}'
            ]
        self.set_cookies(command)
        self.set_language(command)
        self.set_proxy(command)
        channel_name = w.worker(command).output().strip().replace('"', '')
        
        # If uploader is empty, NA, or literally "channel", try channel field
        if not channel_name or channel_name == 'NA' or channel_name.lower() == 'channel':
            command = ['yt-dlp', 
                        '--compat-options', 'no-youtube-unavailable-videos',
                        '--print', '%(channel)s',
                        '--restrict-filenames',
                        '--ignore-errors',
                        '--no-warnings',
                        '--playlist-items', '1',
                        '--compat-options', 'no-youtube-channel-redirect',
                        f'{self.channel_url}'
            ]
            self.set_cookies(command)
            self.set_language(command)
            self.set_proxy(command)
            channel_name = w.worker(command).output().strip().replace('"', '')
        
        # Final fallback: use URL
        if not channel_name or channel_name == 'NA':
            channel_name = self.channel_url.split('/')[-1]
        
        self.channel_name = channel_name
        return sanitize(self.channel_name)
     
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
            self.set_cookies(command)
            self.set_language(command)
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
            

            self.channel_description = w.worker(command).shell()
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
            self.set_cookies(command)
            self.set_language(command)
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
                self.channel_description = w.worker(command).shell()
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
        command = ['yt-dlp', 
                    '--list-thumbnails',
                    '--restrict-filenames',
                    '--ignore-errors',
                    '--no-warnings',
                    '--playlist-items', '0',
                    self.channel_url
        ]
        self.set_cookies(command)
        self.set_language(command)
        self.set_proxy(command)
        landscape = None
        poster = None
        
        try:
            output = w.worker(command).output()
            lines = output.split('\n')

            # Parse thumbnails looking for specific IDs
            for line in lines:
                line = line.strip()
                
                # Look for avatar_uncropped (poster)
                if 'avatar_uncropped' in line:
                    parts = line.split()
                    # URL is the last part
                    if len(parts) >= 4:
                        poster = parts[-1]
                
                # Look for banner_uncropped (landscape)
                if 'banner_uncropped' in line:
                    parts = line.split()
                    # URL is the last part
                    if len(parts) >= 4:
                        landscape = parts[-1]
                        
        except Exception as e:
            l.log("youtube", f"Error getting channel images: {e}")
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
        # Only add cookies if cookie_value is not empty
        if cookie_value and cookie_value.strip():
            command.append(f'--{cookies}')
            command.append(cookie_value)
    
    def set_language(self, command):
        """Configura el idioma para YouTube según la configuración.

        - Añade --extractor-args youtube:lang=<lang> (idioma de metadatos/UI).
        - Añade -S "lang:<lang>" para priorizar la pista de audio del idioma
          configurado cuando el video tiene varias (doblajes). Issue #105.
        """
        extractor_args = []

        if lang and lang.strip():
            extractor_args.append(f'youtube:lang={lang}')
            # Priorizar audio track del idioma configurado sin romper si no existe
            if '-S' not in command and '--format-sort' not in command:
                command.extend(['-S', f'lang:{lang}'])

        # Agregar skip=authcheck para evitar errores con playlists que requieren autenticación
        extractor_args.append('youtubetab:skip=authcheck')

        if extractor_args:
            command.extend(['--extractor-args', ';'.join(extractor_args)])


def get_subtitle_info_from_video_info(video_info, preferred_lang=None):
    preferred_lang = preferred_lang or (lang if lang and lang.strip() else 'en')
    subtitle_sources = []
    for source_name in ('subtitles', 'automatic_captions'):
        source = video_info.get(source_name) or {}
        for subtitle_lang, subtitle_entries in source.items():
            subtitle_sources.append((subtitle_lang, subtitle_entries))

    if not subtitle_sources:
        return None

    def lang_score(subtitle_lang):
        if subtitle_lang == preferred_lang:
            return 0
        if subtitle_lang.startswith(f'{preferred_lang}-'):
            return 1
        if preferred_lang.startswith(f'{subtitle_lang}-'):
            return 2
        if subtitle_lang.split('-')[0] == preferred_lang.split('-')[0]:
            return 3
        if subtitle_lang.startswith('en'):
            return 4
        return 5

    subtitle_sources.sort(key=lambda item: lang_score(item[0]))

    for subtitle_lang, subtitle_entries in subtitle_sources:
        vtt_entries = [entry for entry in subtitle_entries if entry.get('ext') == 'vtt' and entry.get('url')]
        entries = vtt_entries or [entry for entry in subtitle_entries if entry.get('url')]
        if entries:
            return {
                'lang': subtitle_lang,
                'name': subtitle_lang,
                'url': entries[0]['url']
            }

    return None

def get_subtitle_info(youtube_id, preferred_lang=None):
    command = [
        'yt-dlp',
        '-j',
        '--skip-download',
        '--no-warnings',
        f'https://www.youtube.com/watch?v={youtube_id}'
    ]
    Youtube().set_cookies(command)
    Youtube().set_language(command)
    Youtube().set_proxy(command)
    try:
        video_info = json.loads(w.worker(command).output())
        return get_subtitle_info_from_video_info(video_info, preferred_lang)
    except Exception as e:
        l.log("youtube", f"Error getting subtitles for {youtube_id}: {e}")
        return None

def download_subtitles_for_video(youtube_id, file_path):
    if not download_subtitles or '-audio' in youtube_id:
        return

    base_path = os.path.splitext(file_path)[0]
    subtitle_dir = os.path.dirname(base_path)
    subtitle_base = os.path.basename(base_path)
    if os.path.isdir(subtitle_dir):
        for fname in os.listdir(subtitle_dir):
            if fname.startswith(subtitle_base + '.') and fname.endswith(('.vtt', '.srt', '.ass')):
                return

    sub_langs = f'{lang},{lang}-orig,en,en-orig'
    command = [
        'yt-dlp',
        '--skip-download',
        '--write-subs',
        '--write-auto-subs',
        '--sub-langs', sub_langs,
        '--sub-format', 'vtt',
        '--no-warnings',
        '--ignore-errors',
        '-o', f'{base_path}.%(ext)s',
        f'https://www.youtube.com/watch?v={youtube_id}'
    ]
    Youtube().set_cookies(command)
    Youtube().set_language(command)
    Youtube().set_proxy(command)
    try:
        w.worker(command).output()
        l.log("youtube", f"Subtitles downloaded for {youtube_id}")
        time.sleep(2)
    except Exception as e:
        l.log("youtube", f"Error downloading subtitles for {youtube_id}: {e}")

def filter_and_modify_bandwidth(m3u8_content, subtitle_info=None, youtube_id=None):
    lines = m3u8_content.splitlines()

    highest_bandwidth = 0
    best_video_info = None
    best_video_url = None

    media_lines = []

    # Issue #110 / PR #115: YouTube auto-dubbed videos expose per-language
    # variants in the HLS manifest via YT-EXT-AUDIO-CONTENT-ID (e.g. "en-US.3").
    # When at least one stream declares a language, prefer streams matching the
    # configured `lang`; otherwise keep the pure highest-bandwidth logic.
    yt_audio_lang_re = re.compile(r'YT-EXT-AUDIO-CONTENT-ID="([^."]+)')
    sel_by_lang = False
    if lang and lang.strip():
        for line in lines:
            if line.startswith("#EXT-X-STREAM-INF:"):
                match = yt_audio_lang_re.search(line)
                if match and match.group(1):
                    sel_by_lang = True
                    break

    for i in range(len(lines)):
        line = lines[i]

        if line.startswith("#EXT-X-STREAM-INF:") and i + 1 < len(lines):
            info = line
            url = lines[i + 1]
            try:
                bandwidth = int(info.split("BANDWIDTH=")[1].split(",")[0])
            except:
                bandwidth = 0

            desired_lang = not sel_by_lang
            if sel_by_lang:
                match = yt_audio_lang_re.search(info)
                if match and match.group(1):
                    info_lang = match.group(1)
                    # Handle "en" vs "en-US" in either direction
                    if (lang.startswith(info_lang)
                            or info_lang.startswith(lang)
                            or info_lang == lang):
                        desired_lang = True

            if bandwidth > highest_bandwidth and desired_lang:
                highest_bandwidth = bandwidth
                best_video_info = info
                best_video_url = url

        if line.startswith("#EXT-X-MEDIA:"):
            media_lines.append(line)

    # Fallback: if language filtering rejected everything (e.g. the configured
    # lang is not present at all in the manifest), relax the filter and pick
    # the highest bandwidth variant so playback is not broken.
    if sel_by_lang and best_video_url is None:
        for i in range(len(lines)):
            line = lines[i]
            if line.startswith("#EXT-X-STREAM-INF:") and i + 1 < len(lines):
                info = line
                url = lines[i + 1]
                try:
                    bandwidth = int(info.split("BANDWIDTH=")[1].split(",")[0])
                except:
                    bandwidth = 0
                if bandwidth > highest_bandwidth:
                    highest_bandwidth = bandwidth
                    best_video_info = info
                    best_video_url = url

    # Create the final M3U8 content
    final_m3u8 = "#EXTM3U\n#EXT-X-INDEPENDENT-SEGMENTS\n"
    
    # Add all EXT-X-MEDIA lines
    for media_line in media_lines:
        final_m3u8 += f"{media_line}\n"

    if subtitle_info and youtube_id:
        subtitle_lang = subtitle_info['lang']
        subtitle_name = subtitle_info['name']
        subtitle_uri = f"/youtube/subtitles/{youtube_id}.vtt?lang={quote(subtitle_lang)}"
        final_m3u8 += f'#EXT-X-MEDIA:TYPE=SUBTITLES,GROUP-ID="subs",NAME="{subtitle_name}",DEFAULT=YES,AUTOSELECT=YES,LANGUAGE="{subtitle_lang}",URI="{subtitle_uri}"\n'
        if best_video_info and 'SUBTITLES=' not in best_video_info:
            best_video_info = f'{best_video_info},SUBTITLES="subs"'

    if best_video_info and best_video_url:
        final_m3u8 += f"{best_video_info}\n{best_video_url}\n"

    return final_m3u8

def clean_text(text):
    # Reemplazar los caracteres especiales habituales y eliminar los que no son necesarios

    # Escapando caracteres que deben mantenerse pero asegurándote de que sean seguros
    text = html.escape(text)
    
    # Eliminar cualquier carácter no deseado usando expresiones regulares
    text = re.sub(r'[^\w\s\[\]\(\)\-\_\'\"\/\.\:\;\,]', '', text)
    
    return text

def video_id_exists_in_content(media_folder, video_id):
    for root, dirs, files in os.walk(media_folder):
        for file in files:
            if file.endswith(".strm"):
                file_path = os.path.join(root, file)
                with open(file_path, 'r') as f:
                    if video_id in f.read():
                        return True
    return False

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
            # Reverse video list so oldest videos get lower episode numbers
            videos.reverse()
            channel_nfo = False
            channel_folder_created = False
            
            # Get channel_id from first video to create channel folder and NFO
            first_video = videos[0]
            channel_id = first_video['channel_id']
            youtube_channel_folder = first_video['uploader_id'].replace('/user/','@').replace('/streams','')
            
            # Create channel folder
            channel_folder = sanitize(
                "{} [{}]".format(
                    youtube_channel_folder,
                    channel_id
                )
            )
            f.folders().make_clean_folder(
                "{}/{}".format(media_folder, channel_folder),
                False,
                ytdlp2strm_config
            )
            
            # Create channel NFO with correct images
            n.nfo(
                "tvshow",
                "{}/{}".format(media_folder, channel_folder),
                {
                    "title" : channel_name,
                    "plot" : channel_description.replace('\n', ' <br/>'),
                    "landscape" : yt.channel_landscape,
                    "poster" : yt.channel_poster,
                    "studio" : "Youtube"
                }
            ).make_nfo()
            channel_nfo = True
            channel_folder_created = True
            
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

                channel_folder = sanitize(
                    "{} [{}]".format(
                        youtube_channel_folder,
                        channel_id
                    )
                )
                
                # Create season folder based on video year
                season_folder = f"Season {year}"
                folder_full_path = "{}/{}/{}".format(media_folder, channel_folder, season_folder)
                
                # Format title with episode number
                use_mmdd = (episode_format.lower() == 'mmdd')
                formatted_title = format_episode_title(video_name, folder_full_path, upload_date, use_mmdd)
                
                file_path = "{}/{}/{}/{}.{}".format(
                    media_folder,
                    channel_folder,
                    season_folder,
                    sanitize(formatted_title),
                    "strm"
                )

                folder_path = "{}/{}".format(
                    media_folder, 
                    sanitize(
                        "{} [{}]".format(
                            youtube_channel_folder,
                            channel_id
                        )
                    )
                )

                if video_id_exists_in_content(folder_path, video_id):
                    l.log("youtube", f'Video {video_id} already exists')
                    download_subtitles_for_video(video_id, file_path)
                    continue

                if not channel_folder_created:
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
                    channel_folder_created = True
                
                # Create season folder if it doesn't exist
                season_folder_path = "{}/{}/{}".format(media_folder, channel_folder, season_folder)
                if not os.path.exists(season_folder_path):
                    os.makedirs(season_folder_path, exist_ok=True)

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
                            "title" : channel_name,  # Use friendly name instead of @-handle
                            "plot" : channel_description.replace('\n', ' <br/>'),
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
                    "{}/{}/{}".format(
                        media_folder, 
                        "{} [{}]".format(
                            youtube_channel,
                            channel_id
                        ),
                        season_folder
                    ),
                    {
                        "item_name" : sanitize(formatted_title),
                        "title" : sanitize(formatted_title),
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
                download_subtitles_for_video(video_id, file_path)
            
            # Notify Jellyfin/Emby after processing all videos for this channel
            jellyfin_notifier = JellyfinNotifier(config)
            if jellyfin_notifier.enabled:
                jellyfin_notifier.notify_new_content(f"{media_folder}/{channel_folder}")
        else:
            log_text = (" no videos detected...") 
            l.log("youtube", log_text)


def direct(youtube_id, remote_addr):
    current_time = time.time()
    cache_key = f"{remote_addr}_{youtube_id}"
    
    # Check if the request is already cached
    if cache_key not in recent_requests:
        log_text = f'[{remote_addr}] Playing {youtube_id}'
        l.log("youtube", log_text)
        recent_requests[cache_key] = current_time

    if '-audio' not in youtube_id:
        extractor_args = ['youtube:player-client=default,web_safari']
        if lang and lang.strip():
            extractor_args.append(f'youtube:lang={lang}')
        extractor_args.append('youtubetab:skip=authcheck')
        command = [
            'yt-dlp', 
            '-j',
            '--no-warnings',
            '--extractor-args', ';'.join(extractor_args),
            f'https://www.youtube.com/watch?v={youtube_id}'
        ]
        Youtube().set_cookies(command)
        Youtube().set_proxy(command)
        full_info_json_str = w.worker(command).output()
        m3u8_url = None
        subtitle_info = None
        try:
            full_info_json = json.loads(full_info_json_str)
            subtitle_info = get_subtitle_info_from_video_info(full_info_json)

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
                f'https://www.youtube.com/watch?v={youtube_id}'
            ]
            Youtube().set_cookies(command)
            Youtube().set_language(command)
            Youtube().set_proxy(command)
            sd_url = w.worker(command).output()
            return redirect(sd_url.strip(), 301)
        else:
            response = requests.get(m3u8_url, timeout=15)
            if response.status_code == 200:
                # Ensure UTF-8 encoding
                response.encoding = 'utf-8'
                m3u8_content = response.text
                filtered_content = filter_and_modify_bandwidth(m3u8_content, subtitle_info, youtube_id)
                
                # Create Response with headers optimized for VLC and media players
                flask_response = Response(filtered_content, mimetype='application/vnd.apple.mpegurl')
                flask_response.headers['Content-Type'] = 'application/vnd.apple.mpegurl; charset=utf-8'
                flask_response.headers['Content-Disposition'] = 'inline; filename="index.m3u8"'
                flask_response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
                flask_response.headers['Pragma'] = 'no-cache'
                flask_response.headers['Expires'] = '0'
                flask_response.headers['Accept-Ranges'] = 'bytes'
                flask_response.headers['Access-Control-Allow-Origin'] = '*'
                flask_response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
                flask_response.headers['Access-Control-Allow-Headers'] = 'Range'
                
                return flask_response
    else:
        s_youtube_id = youtube_id.split('-audio')[0]
        command = [
            'yt-dlp',
            '-f', 'bestaudio',
            '--get-url',
            '--no-warnings',
            f'https://www.youtube.com/watch?v={s_youtube_id}'
        ]
        Youtube().set_cookies(command)
        Youtube().set_language(command)
        Youtube().set_proxy(command)
        audio_url = w.worker(command).output()
        return redirect(audio_url, 301)

    return "Manifest URL not found or failed to redirect.", 404

def subtitles(youtube_id):
    subtitle_lang = request.args.get('lang')
    subtitle_info = get_subtitle_info(youtube_id, subtitle_lang)
    if not subtitle_info:
        return "Subtitles not found.", 404

    try:
        response = requests.get(subtitle_info['url'], timeout=15)
        if response.status_code != 200:
            return "Subtitles not found.", 404
        flask_response = Response(response.content, mimetype='text/vtt')
        flask_response.headers['Content-Type'] = 'text/vtt; charset=utf-8'
        flask_response.headers['Cache-Control'] = 'public, max-age=3600'
        flask_response.headers['Access-Control-Allow-Origin'] = '*'
        return flask_response
    except Exception as e:
        l.log("youtube", f"Error serving subtitles for {youtube_id}: {e}")
        return "Subtitles not found.", 404
    
def bridge(youtube_id):
    s_youtube_id = youtube_id.split('-audio')[0]
    s_youtube_id_url = f'https://www.youtube.com/watch?v={s_youtube_id}'

    # Get info for duration and size
    duration = None
    file_size = None
    try:
        command_info = ['yt-dlp', '--dump-json', '--no-warnings', s_youtube_id_url]
        Youtube().set_cookies(command_info)
        Youtube().set_proxy(command_info)
        info = json.loads(w.worker(command_info).output())
        
        duration = info.get('duration')
        file_size = info.get('filesize') or info.get('filesize_approx')
    except Exception as e:
        l.log("youtube", f"Error getting info: {e}")

    # Parse Range Header
    range_header = request.headers.get('Range', None)
    byte_start = 0
    byte_end = None
    length = file_size

    if range_header and file_size:
        match = re.search(r'(\d+)-(\d*)', range_header)
        if match:
            start_str, end_str = match.groups()
            byte_start = int(start_str)
            if end_str:
                byte_end = int(end_str)
            else:
                byte_end = file_size - 1
            
            length = byte_end - byte_start + 1

    # Calculate start time for yt-dlp
    start_time = 0
    if byte_start > 0 and file_size and duration:
        start_time = (byte_start / file_size) * duration

    def generate():
        if config["sponsorblock"]:
            command = ['yt-dlp', '--no-warnings', '-o', '-', '-f', 'bestvideo+bestaudio', '--sponsorblock-remove',  config['sponsorblock_cats'], '--restrict-filenames']
        else:
            command = ['yt-dlp', '--no-warnings', '-o', '-', '-f', 'best', '--restrict-filenames']

        if start_time > 0:
            command.extend(['--download-sections', f'*{start_time}-inf'])
        
        command.append(s_youtube_id_url)
        
        Youtube().set_cookies(command)
        Youtube().set_language(command)
        Youtube().set_proxy(command)

        if '-audio' in youtube_id:
            try:
                f_index = command.index('-f')
                command[f_index + 1] = 'bestaudio'
            except ValueError:
                pass
        
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        
        try:
            while True:
                data = process.stdout.read(4096)
                if not data:
                    break
                yield data
        finally:
            process.kill()

    response = Response(
        stream_with_context(generate()), 
        mimetype = "video/mp4"
    )

    response.headers['Accept-Ranges'] = 'bytes'
    if file_size:
        response.headers['Content-Length'] = str(length)
        if range_header:
            response.status_code = 206
            response.headers['Content-Range'] = f'bytes {byte_start}-{byte_end}/{file_size}'

    return response 

def download(youtube_id):
    s_youtube_id = youtube_id.split('-audio')[0]
    current_dir = os.getcwd()

    # Construyes la ruta hacia la carpeta 'temp' dentro del directorio actual
    temp_dir = os.path.join(current_dir, 'temp')
    if config["sponsorblock"]:
        command = ['yt-dlp', '-f', 'bv*+ba+ba.2', '-o',  os.path.join(temp_dir, '%(title)s.%(ext)s'), '--sponsorblock-remove',  config['sponsorblock_cats'], '--restrict-filenames', s_youtube_id]
    else:
        command = ['yt-dlp', '-f', 'bv*+ba+ba.2', '-o',  os.path.join(temp_dir, '%(title)s.%(ext)s'), '--restrict-filenames', s_youtube_id]
    Youtube().set_cookies(command)
    Youtube().set_language(command)
    Youtube().set_proxy(command)
    if '-audio' in youtube_id:
        command[2] = 'bestaudio'

    w.worker(command).call()
    
    filename_command = ['yt-dlp', '--print', 'filename', '--restrict-filenames', "{}".format(youtube_id)]
    Youtube().set_cookies(filename_command)
    Youtube().set_language(filename_command)
    filename = w.worker(filename_command).output()
    return send_file(
        os.path.join(temp_dir, filename)
    )