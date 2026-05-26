import os
import json
import time
import platform
import subprocess
import threading
import requests
import html
import re
from datetime import datetime
from cachetools import TTLCache
from urllib.parse import quote, urljoin
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
direct_stream_cache = TTLCache(maxsize=500, ttl=1800)
direct_neighbor_cache = TTLCache(maxsize=5000, ttl=86400)
direct_prewarm_inflight = TTLCache(maxsize=1000, ttl=600)
direct_neighbor_index_inflight = TTLCache(maxsize=1, ttl=600)
direct_prewarm_lock = threading.Lock()
direct_prewarm_semaphore = threading.Semaphore(2)
DIRECT_CACHE_VERSION = "v4"

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
    video_quality = str(config["video_quality"]).strip().lower()
except:
    video_quality = "best"

def _get_video_quality_height():
    if not video_quality or video_quality in ("best", "0", "none", "default"):
        return None
    match = re.search(r'\d+', video_quality)
    if not match:
        return None
    return int(match.group(0))

def _get_video_format_selector(default_selector='best'):
    max_height = _get_video_quality_height()
    if not max_height:
        return default_selector
    return f'bestvideo[height<={max_height}]+bestaudio/best[height<={max_height}]/best'

def _quality_cache_tag():
    """Tag used in cache keys/filenames so changing video_quality in config
    invalidates the previous direct-stream caches. Issue #119: without this,
    a cached low-quality variant URL keeps being served until the TTL expires.
    """
    height = _get_video_quality_height()
    return f"h{height}" if height else "best"

try:
    download_subtitles = str(config["download_subtitles"]).lower() in ("true", "1", "yes", "on")
except:
    download_subtitles = False

try:
    convert_subtitles_to_srt = str(config["convert_subtitles_to_srt"]).lower() in ("true", "1", "yes", "on")
except:
    convert_subtitles_to_srt = False

try:
    keep_vtt_subtitles = str(config["keep_vtt_subtitles"]).lower() in ("true", "1", "yes", "on")
except:
    keep_vtt_subtitles = True

try:
    direct_stream_cache_hours = int(config["direct_stream_cache_hours"])
except:
    direct_stream_cache_hours = 4

try:
    direct_serve_media_playlist = str(config["direct_serve_media_playlist"]).lower() in ("true", "1", "yes", "on")
except:
    direct_serve_media_playlist = False

try:
    direct_prewarm_latest_per_channel = int(config["direct_prewarm_latest_per_channel"])
except:
    direct_prewarm_latest_per_channel = 1

try:
    direct_prewarm_neighbors = str(config["direct_prewarm_neighbors"]).lower() in ("true", "1", "yes", "on")
except:
    direct_prewarm_neighbors = True

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
    
    @staticmethod
    def _normalize_yt_url(url):
        """Force youtube.com / m.youtube.com URLs to www.youtube.com.

        Issue #101: yt-dlp returns 'HTTP Error 400: Bad Request' on the tab
        extractor for some channels when the URL lacks 'www.' (e.g.
        'https://youtube.com/@mkbhd'). Mobile and bare hosts are coerced to
        the canonical www host so the API call succeeds.
        """
        if not url:
            return url
        return re.sub(
            r'://(?:m\.|www\.)?youtube\.com',
            '://www.youtube.com',
            url,
            count=1,
        )

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

            self.channel_url = self._normalize_yt_url(self.channel_url)

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

            self.channel_url = self._normalize_yt_url(self.channel_url)

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

            self.channel_url = self._normalize_yt_url(self.channel_url)

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
                    'uploader_id': sanitize(self.channel_name),
                    'duration': data.get('duration')
                }
                videos.append(video)
        
        return videos
    
    def get_keyword_videos(self):
        keyword = self.channel.split('-')[1]
        command = [
            'yt-dlp', 
            '-f', _get_video_format_selector('best'), 'ytsearch:["{}"]'.format(keyword),
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
                    'uploader_id': data.get('uploader_id'),
                    'duration': data.get('duration')
                }
                videos.append(video)
        
        return videos
    
    def get_keyword_audios(self):
        keyword = self.channel.split('-')[1]
        command = [
            'yt-dlp', 
            '-f', _get_video_format_selector('best'), 'ytsearch10:["{}"]'.format(keyword),
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
                    'uploader_id': data.get('uploader_id'),
                    'duration': data.get('duration')
                }
                videos.append(video)
        
        return videos
    
    def get_channel_audios(self):
        cu = self.channel_url

        if not '/streams' in self.channel_url:
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
                    'uploader_id': data.get('uploader_id'),
                    'duration': data.get('duration')
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
                    'uploader_id': sanitize(self.channel_name),
                    'duration': data.get('duration')
                }
                videos.append(video)
        
        return videos
    
    def get_channel_videos(self):
        cu = self.channel_url

        if not '/streams' in self.channel_url:
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
                    'id': data.get('id'),
                    'title': data.get('title'),
                    'upload_date': data.get('upload_date'),
                    'thumbnail': data.get('thumbnail'),
                    'description': data.get('description'),
                    'channel_id': data.get('channel_id'),
                    'uploader_id': data.get('uploader_id'),
                    'duration': data.get('duration')
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

def _clean_vtt_text_line(line):
    """Strip YouTube karaoke/continuation markers from a cue text line."""
    # Remove inline timestamps like <00:00:01.120>
    line = re.sub(r'<\d{2}:\d{2}:\d{2}\.\d{3}>', '', line)
    # Remove <c> / </c> continuation tags
    line = re.sub(r'</?c[._\w]*>', '', line)
    return line

def _fix_vtt_cue_timing_line(line):
    """Normalize timing line: center alignment, drop positional offsets."""
    line = re.sub(r'\s+position:\d+(\.\d+)?%', '', line)
    line = re.sub(r'\s+line:\d+(\.\d+)?%', '', line)
    line = re.sub(r'\s+line:\d+', '', line)
    if re.search(r'\balign:(start|left)\b', line):
        line = re.sub(r'\balign:(start|left)\b', 'align:middle', line)
    elif not re.search(r'\balign:\w+\b', line):
        line += ' align:middle'
    return line

def _fix_vtt_alignment(vtt_text):
    """Post-process a WebVTT string for Emby/Jellyfin compatibility.

    Fixes two issues with YouTube auto-generated captions:
      1. Left alignment ('align:start' + 'position:..%') -> center.
      2. Rollup/persiana effect: YouTube emits each cue containing the
         *previous* line plus the *new* line, plus tiny transition cues
         that re-show the previous line alone. We collapse each cue to
         only the last (newest) text line and drop redundant cues.
    """
    # Split header from body: header is everything until the first blank
    # line followed by a cue (or just keep everything up to first '-->').
    parts = re.split(r'\r?\n\r?\n', vtt_text)
    if not parts:
        return vtt_text

    header = parts[0]
    cue_blocks = parts[1:]

    out_blocks = [header]
    last_text = None

    for block in cue_blocks:
        block_lines = block.splitlines()
        if not block_lines:
            continue

        # Find timing line (the one with -->)
        timing_idx = None
        for i, ln in enumerate(block_lines):
            if '-->' in ln:
                timing_idx = i
                break
        if timing_idx is None:
            # Not a cue (could be NOTE / STYLE / etc) - keep as is
            out_blocks.append(block)
            continue

        timing_line = _fix_vtt_cue_timing_line(block_lines[timing_idx])
        text_lines = [_clean_vtt_text_line(l) for l in block_lines[timing_idx + 1:]]

        # Filter empty / whitespace-only lines
        non_empty = [l for l in text_lines if l.strip()]
        if not non_empty:
            # Skip cues that contain no real text after cleaning
            continue

        # Keep ONLY the last non-empty text line (the newest)
        new_text = non_empty[-1].rstrip()

        # Skip duplicates (consecutive cues showing same text)
        if new_text == last_text:
            continue
        last_text = new_text

        cue = []
        # Preserve any cue identifier lines before the timing line
        cue.extend(block_lines[:timing_idx])
        cue.append(timing_line)
        cue.append(new_text)
        out_blocks.append('\n'.join(cue))

    return '\n\n'.join(out_blocks)

def _vtt_timestamp_to_srt(timestamp):
    return timestamp.strip().replace('.', ',')

def _vtt_text_to_srt(vtt_text):
    blocks = re.split(r'\r?\n\r?\n', vtt_text)
    srt_blocks = []
    cue_number = 1

    for block in blocks:
        lines = [line.strip('\ufeff') for line in block.splitlines()]
        if not lines:
            continue

        timing_idx = None
        for idx, line in enumerate(lines):
            if '-->' in line:
                timing_idx = idx
                break

        if timing_idx is None:
            continue

        timing_line = lines[timing_idx]
        timing_parts = timing_line.split('-->')
        if len(timing_parts) != 2:
            continue

        start_time = _vtt_timestamp_to_srt(timing_parts[0])
        end_time = _vtt_timestamp_to_srt(timing_parts[1].split()[0])
        text_lines = [_clean_vtt_text_line(line) for line in lines[timing_idx + 1:] if line.strip()]
        text_lines = [re.sub(r'<[^>]+>', '', line).strip() for line in text_lines]
        text_lines = [line for line in text_lines if line]
        if not text_lines:
            continue

        srt_blocks.append(f"{cue_number}\n{start_time} --> {end_time}\n" + "\n".join(text_lines))
        cue_number += 1

    return "\n\n".join(srt_blocks) + ("\n" if srt_blocks else "")

def _convert_vtt_file_to_srt(vtt_path):
    srt_path = os.path.splitext(vtt_path)[0] + ".srt"
    with open(vtt_path, 'r', encoding='utf-8') as f:
        vtt_text = f.read()
    srt_text = _vtt_text_to_srt(_fix_vtt_alignment(vtt_text))
    if not srt_text:
        return False
    with open(srt_path, 'w', encoding='utf-8') as f:
        f.write(srt_text)
    if not keep_vtt_subtitles:
        try:
            os.remove(vtt_path)
        except:
            pass
    return True

def _convert_vtt_files_to_srt_in_subtitle_dir(subtitle_dir, subtitle_base):
    converted_count = 0
    if os.path.isdir(subtitle_dir):
        for fname in os.listdir(subtitle_dir):
            if fname.startswith(subtitle_base + '.') and fname.endswith('.vtt'):
                vtt_path = os.path.join(subtitle_dir, fname)
                try:
                    if _convert_vtt_file_to_srt(vtt_path):
                        converted_count += 1
                except Exception as e:
                    l.log("youtube", f"Error converting VTT to SRT for {fname}: {e}")
    return converted_count

def _fix_vtt_files_in_subtitle_dir(subtitle_dir, subtitle_base):
    fixed_count = 0
    if os.path.isdir(subtitle_dir):
        for fname in os.listdir(subtitle_dir):
            if fname.startswith(subtitle_base + '.') and fname.endswith('.vtt'):
                vtt_path = os.path.join(subtitle_dir, fname)
                try:
                    with open(vtt_path, 'r', encoding='utf-8') as f:
                        original = f.read()
                    fixed = _fix_vtt_alignment(original)
                    if fixed != original:
                        with open(vtt_path, 'w', encoding='utf-8') as f:
                            f.write(fixed)
                        fixed_count += 1
                except Exception as e:
                    l.log("youtube", f"Error fixing VTT alignment for {fname}: {e}")
    return fixed_count

def _make_direct_response(m3u8_content):
    flask_response = Response(m3u8_content, mimetype='application/vnd.apple.mpegurl')
    flask_response.headers['Content-Type'] = 'application/vnd.apple.mpegurl; charset=utf-8'
    flask_response.headers['Content-Disposition'] = 'inline; filename="index.m3u8"'
    max_age_seconds = max(1, direct_stream_cache_hours) * 3600
    flask_response.headers['Cache-Control'] = f'public, max-age={max_age_seconds}'
    flask_response.headers['Accept-Ranges'] = 'bytes'
    flask_response.headers['Access-Control-Allow-Origin'] = '*'
    flask_response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
    flask_response.headers['Access-Control-Allow-Headers'] = 'Range'
    return flask_response

def _resolve_direct_m3u8(youtube_id):
    extractor_args = ['youtube:player-client=default,web_safari']
    if lang and lang.strip():
        extractor_args.append(f'youtube:lang={lang}')
    extractor_args.append('youtubetab:skip=authcheck')
    command = [
        'yt-dlp', 
        '-j',
        '--no-playlist',
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
        return None

    response = requests.get(m3u8_url, timeout=15)
    if response.status_code != 200:
        return None

    response.encoding = 'utf-8'
    filtered_content = filter_and_modify_bandwidth(response.text, subtitle_info, youtube_id)
    if direct_serve_media_playlist:
        variant_url = None
        for line in filtered_content.splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                variant_url = stripped
                break
        if variant_url:
            try:
                variant_response = requests.get(variant_url, timeout=15)
                if variant_response.status_code == 200:
                    variant_response.encoding = 'utf-8'
                    media_playlist = _make_media_playlist_absolute(variant_response.text, variant_url)
                    filtered_content = media_playlist
            except Exception as e:
                l.log("youtube", f"Error downloading media playlist for {youtube_id}: {e}")
    return filtered_content

def _make_media_playlist_absolute(m3u8_content, playlist_url):
    absolute_lines = []
    uri_re = re.compile(r'URI="([^"]+)"')
    for line in m3u8_content.splitlines():
        stripped = line.strip()
        if not stripped:
            absolute_lines.append(line)
            continue
        if stripped.startswith("#"):
            absolute_lines.append(uri_re.sub(lambda m: f'URI="{urljoin(playlist_url, m.group(1))}"', line))
            continue
        absolute_lines.append(urljoin(playlist_url, stripped))
    return "\n".join(absolute_lines) + "\n"

def _get_stream_inf_height(info):
    match = re.search(r'\bRESOLUTION=\d+x(\d+)', info)
    if not match:
        return None
    try:
        return int(match.group(1))
    except:
        return None

def _is_direct_stream_cache_valid(cache_path):
    if not os.path.isfile(cache_path):
        return False

    max_age_seconds = max(1, direct_stream_cache_hours) * 3600
    return (time.time() - os.path.getmtime(cache_path)) < max_age_seconds

def _direct_stream_cache_path(youtube_id):
    # Issue #119: include the quality tag in the filename so changing
    # video_quality in config invalidates previously-cached variant URLs.
    return os.path.join(media_folder, ".direct_cache", f"{youtube_id}.{lang}.{_quality_cache_tag()}.{DIRECT_CACHE_VERSION}.m3u8")

def _save_direct_stream_to_disk(youtube_id, m3u8_content):
    cache_dir = os.path.join(media_folder, ".direct_cache")
    cache_path = _direct_stream_cache_path(youtube_id)
    try:
        os.makedirs(cache_dir, exist_ok=True)
        with open(cache_path, 'w', encoding='utf-8') as f:
            f.write(m3u8_content)
    except Exception as e:
        l.log("youtube", f"Error saving direct stream cache for {youtube_id}: {e}")

def _load_direct_stream_from_disk(youtube_id):
    cache_path = _direct_stream_cache_path(youtube_id)
    if _is_direct_stream_cache_valid(cache_path):
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                content = f.read()
                return content
        except:
            pass
    return None

def _is_direct_stream_cached(youtube_id):
    stream_cache_key = f"{youtube_id}:{lang}:{_quality_cache_tag()}"
    return stream_cache_key in direct_stream_cache or _is_direct_stream_cache_valid(_direct_stream_cache_path(youtube_id))

def _prewarm_direct_stream(youtube_id, reason):
    if not youtube_id or '-audio' in youtube_id or _is_direct_stream_cached(youtube_id):
        return

    with direct_prewarm_lock:
        if youtube_id in direct_prewarm_inflight:
            return
        direct_prewarm_inflight[youtube_id] = time.time()

    def worker():
        started_at = time.time()
        direct_prewarm_semaphore.acquire()
        try:
            if _is_direct_stream_cached(youtube_id):
                return
            l.log("youtube", f"[direct-prewarm] start {youtube_id} reason={reason}")
            m3u8_content = _resolve_direct_m3u8(youtube_id)
            if m3u8_content:
                direct_stream_cache[f"{youtube_id}:{lang}:{_quality_cache_tag()}"] = m3u8_content
                _save_direct_stream_to_disk(youtube_id, m3u8_content)
                l.log("youtube", f"[direct-prewarm] done {youtube_id} reason={reason} elapsed={time.time() - started_at:.3f}s bytes={len(m3u8_content)}")
            else:
                l.log("youtube", f"[direct-prewarm] skipped {youtube_id} reason={reason} elapsed={time.time() - started_at:.3f}s")
        except Exception as e:
            l.log("youtube", f"[direct-prewarm] error {youtube_id} reason={reason}: {e}")
        finally:
            direct_prewarm_semaphore.release()
            with direct_prewarm_lock:
                if youtube_id in direct_prewarm_inflight:
                    del direct_prewarm_inflight[youtube_id]

    threading.Thread(target=worker, daemon=True).start()

def _index_direct_neighbors(videos):
    video_ids = [video.get('id') for video in videos if video.get('id')]
    for idx, video_id in enumerate(video_ids):
        previous_id = video_ids[idx - 1] if idx > 0 else None
        next_id = video_ids[idx + 1] if idx + 1 < len(video_ids) else None
        direct_neighbor_cache[video_id] = (previous_id, next_id)

def _extract_direct_video_id_from_strm(strm_path):
    try:
        with open(strm_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        match = re.search(r'/youtube/(?:direct|redirect)/([^/?\s]+)', content)
        if match:
            return match.group(1)
    except:
        pass
    return None

def _index_direct_neighbors_from_disk(seed_youtube_id=None):
    with direct_prewarm_lock:
        if "disk-index" in direct_neighbor_index_inflight:
            return
        direct_neighbor_index_inflight["disk-index"] = time.time()

    def worker():
        started_at = time.time()
        indexed = 0
        try:
            for root, dirs, files in os.walk(media_folder):
                strm_files = sorted(file for file in files if file.endswith(".strm"))
                video_ids = []
                for file in strm_files:
                    video_id = _extract_direct_video_id_from_strm(os.path.join(root, file))
                    if video_id:
                        video_ids.append(video_id)
                for idx, video_id in enumerate(video_ids):
                    previous_id = video_ids[idx - 1] if idx > 0 else None
                    next_id = video_ids[idx + 1] if idx + 1 < len(video_ids) else None
                    direct_neighbor_cache[video_id] = (previous_id, next_id)
                    indexed += 1
            l.log("youtube", f"[direct-neighbors] indexed_from_disk={indexed} elapsed={time.time() - started_at:.3f}s")
            if seed_youtube_id:
                neighbors = direct_neighbor_cache.get(seed_youtube_id)
                if neighbors:
                    for neighbor_id in neighbors:
                        if neighbor_id:
                            _prewarm_direct_stream(neighbor_id, f"neighbor:{seed_youtube_id}")
        except Exception as e:
            l.log("youtube", f"[direct-neighbors] disk index error: {e}")
        finally:
            with direct_prewarm_lock:
                if "disk-index" in direct_neighbor_index_inflight:
                    del direct_neighbor_index_inflight["disk-index"]

    threading.Thread(target=worker, daemon=True).start()

def _prewarm_direct_neighbors(youtube_id):
    if not direct_prewarm_neighbors:
        return

    neighbors = direct_neighbor_cache.get(youtube_id)
    if not neighbors:
        _index_direct_neighbors_from_disk(youtube_id)
        return

    for neighbor_id in neighbors:
        if neighbor_id:
            _prewarm_direct_stream(neighbor_id, f"neighbor:{youtube_id}")

def _prewarm_latest_direct_streams(videos):
    if direct_prewarm_latest_per_channel <= 0:
        return

    latest_videos = list(reversed(videos[-direct_prewarm_latest_per_channel:]))
    for video in latest_videos:
        _prewarm_direct_stream(video.get('id'), "latest-channel-video")

def download_subtitles_for_video(youtube_id, file_path):
    if not download_subtitles or '-audio' in youtube_id:
        return

    base_path = os.path.splitext(file_path)[0]
    subtitle_dir = os.path.dirname(base_path)
    subtitle_base = os.path.basename(base_path)
    if os.path.isdir(subtitle_dir):
        for fname in os.listdir(subtitle_dir):
            if fname.startswith(subtitle_base + '.') and fname.endswith(('.vtt', '.srt', '.ass')):
                fixed_count = _fix_vtt_files_in_subtitle_dir(subtitle_dir, subtitle_base)
                if fixed_count:
                    l.log("youtube", f"Fixed VTT alignment for {fixed_count} subtitle file(s) of {youtube_id}")
                if convert_subtitles_to_srt:
                    converted_count = _convert_vtt_files_to_srt_in_subtitle_dir(subtitle_dir, subtitle_base)
                    if converted_count:
                        l.log("youtube", f"Converted {converted_count} VTT subtitle file(s) to SRT for {youtube_id}")
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
        fixed_count = _fix_vtt_files_in_subtitle_dir(subtitle_dir, subtitle_base)
        if fixed_count:
            l.log("youtube", f"Fixed VTT alignment for {fixed_count} subtitle file(s) of {youtube_id}")
        if convert_subtitles_to_srt:
            converted_count = _convert_vtt_files_to_srt_in_subtitle_dir(subtitle_dir, subtitle_base)
            if converted_count:
                l.log("youtube", f"Converted {converted_count} VTT subtitle file(s) to SRT for {youtube_id}")
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
    audio_group_re = re.compile(r'\bAUDIO="([^"]+)"')
    group_id_re = re.compile(r'\bGROUP-ID="([^"]+)"')
    media_lang_re = re.compile(r'\bLANGUAGE="([^"]+)"')
    default_re = re.compile(r'\bDEFAULT=YES\b')
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

            max_height = _get_video_quality_height()
            stream_height = _get_stream_inf_height(info)
            desired_quality = not max_height or not stream_height or stream_height <= max_height

            if bandwidth > highest_bandwidth and desired_lang and desired_quality:
                highest_bandwidth = bandwidth
                best_video_info = info
                best_video_url = url

        if line.startswith("#EXT-X-MEDIA:"):
            media_lines.append(line)

    # Fallback: if language filtering rejected everything (e.g. the configured
    # lang is not present at all in the manifest), relax the filter and pick
    # the highest bandwidth variant so playback is not broken.
    if best_video_url is None:
        for i in range(len(lines)):
            line = lines[i]
            if line.startswith("#EXT-X-STREAM-INF:") and i + 1 < len(lines):
                info = line
                url = lines[i + 1]
                try:
                    bandwidth = int(info.split("BANDWIDTH=")[1].split(",")[0])
                except:
                    bandwidth = 0
                max_height = _get_video_quality_height()
                stream_height = _get_stream_inf_height(info)
                desired_quality = not max_height or not stream_height or stream_height <= max_height
                if bandwidth > highest_bandwidth and desired_quality:
                    highest_bandwidth = bandwidth
                    best_video_info = info
                    best_video_url = url

    if best_video_url is None:
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

    selected_media_lines = []
    selected_audio_group = None
    if best_video_info:
        audio_group_match = audio_group_re.search(best_video_info)
        if audio_group_match:
            selected_audio_group = audio_group_match.group(1)

    if selected_audio_group:
        candidate_media_lines = []
        for media_line in media_lines:
            group_match = group_id_re.search(media_line)
            if group_match and group_match.group(1) == selected_audio_group:
                candidate_media_lines.append(media_line)

        preferred_media_lines = []
        if lang and lang.strip():
            for media_line in candidate_media_lines:
                lang_match = media_lang_re.search(media_line)
                if lang_match:
                    media_lang = lang_match.group(1)
                    if (lang.startswith(media_lang)
                            or media_lang.startswith(lang)
                            or media_lang == lang):
                        preferred_media_lines.append(media_line)

        selected_media_lines = preferred_media_lines
        if not selected_media_lines:
            selected_media_lines = [line for line in candidate_media_lines if default_re.search(line)]
        if not selected_media_lines and candidate_media_lines:
            selected_media_lines = [candidate_media_lines[0]]
    else:
        selected_media_lines = media_lines

    if youtube_id:
        l.log("youtube", f"[direct-manifest] {youtube_id} selected_bandwidth={highest_bandwidth} media_lines={len(selected_media_lines)}/{len(media_lines)}")

    # Create the final M3U8 content
    final_m3u8 = "#EXTM3U\n#EXT-X-INDEPENDENT-SEGMENTS\n"
    
    # Add only EXT-X-MEDIA lines needed by the selected stream
    for media_line in selected_media_lines:
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
    return find_strm_path_for_video_id(media_folder, video_id) is not None

def find_strm_path_for_video_id(media_folder, video_id):
    """Return the absolute path of the .strm file that references video_id,
    or None if no such file exists. Robust to unreadable/locked files."""
    if not os.path.isdir(media_folder):
        return None
    for root, dirs, files in os.walk(media_folder):
        for file in files:
            if file.endswith(".strm"):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        if video_id in f.read():
                            return file_path
                except Exception:
                    continue
    return None

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
            _index_direct_neighbors(videos)
            _prewarm_latest_direct_streams(videos)
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
                # Issue #111: expose duration in the NFO so Jellyfin/Emby
                # can show content length without having to play the video.
                raw_duration = video.get('duration')
                try:
                    duration_seconds = int(raw_duration) if raw_duration else 0
                except (TypeError, ValueError):
                    duration_seconds = 0
                # Kodi/Jellyfin/Emby <runtime> is expressed in minutes.
                runtime_minutes = max(1, (duration_seconds + 59) // 60) if duration_seconds else ""
                year = date.year
                youtube_channel = video['uploader_id']
                youtube_channel_folder = youtube_channel.replace('/user/','@').replace('/streams','')
                # In `iframe` mode the STRM points directly to the public YouTube
                # watch URL, so players that support web/iframe playback (or the
                # user's external app) can resolve it natively without going
                # through ytdlp2STRM.
                if method == 'iframe':
                    file_content = f'https://www.youtube.com/watch?v={video_id}'
                else:
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

                folder_path = "{}/{}".format(
                    media_folder, 
                    sanitize(
                        "{} [{}]".format(
                            youtube_channel_folder,
                            channel_id
                        )
                    )
                )

                # Check first whether this video already has an STRM somewhere
                # in the channel folder. If it does, reuse the EXISTING file path
                # (with its original episode number and title) for subtitle
                # downloads instead of recomputing a new one. Otherwise a renamed
                # YouTube title or an incremented episode counter would generate
                # duplicate .nfo/.png/.vtt/.srt files under a non-existent STRM.
                existing_strm_path = find_strm_path_for_video_id(folder_path, video_id)
                if existing_strm_path:
                    l.log("youtube", f'Video {video_id} already exists at {existing_strm_path}')
                    download_subtitles_for_video(video_id, existing_strm_path)
                    continue

                # Format title with episode number (only for NEW videos)
                use_mmdd = (episode_format.lower() == 'mmdd')
                formatted_title = format_episode_title(video_name, folder_full_path, upload_date, use_mmdd)

                file_path = "{}/{}/{}/{}.{}".format(
                    media_folder,
                    channel_folder,
                    season_folder,
                    sanitize(formatted_title),
                    "strm"
                )

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
                        "preview" : thumbnail,
                        "runtime" : runtime_minutes,
                        "duration_seconds" : duration_seconds or ""
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
    # Issue #119: include the quality tag so cache busts when video_quality changes
    stream_cache_key = f"{youtube_id}:{lang}:{_quality_cache_tag()}"
    
    # Check if the request is already cached
    if cache_key not in recent_requests:
        log_text = f'[{remote_addr}] Playing {youtube_id}'
        l.log("youtube", log_text)
        recent_requests[cache_key] = current_time

    if '-audio' not in youtube_id:
        cached_stream = direct_stream_cache.get(stream_cache_key)
        if cached_stream:
            _prewarm_direct_neighbors(youtube_id)
            return _make_direct_response(cached_stream)

        cached_stream = _load_direct_stream_from_disk(youtube_id)
        if cached_stream:
            direct_stream_cache[stream_cache_key] = cached_stream
            _prewarm_direct_neighbors(youtube_id)
            return _make_direct_response(cached_stream)

        filtered_content = _resolve_direct_m3u8(youtube_id)

        if not filtered_content:
            log_text = ('No manifest detected. Check your cookies config. \n* This video is age-restricted; some formats may be missing without authentication. Use --cookies-from-browser or --cookies for the authentication \n* Serving SD format. Please configure your cookies appropriately to access the manifest that serves the highest quality for this video')
            l.log("youtube", log_text)
            command = [
                'yt-dlp',
                '-f', _get_video_format_selector('best'),
                '--get-url',
                '--no-playlist',
                '--no-warnings',
                f'https://www.youtube.com/watch?v={youtube_id}'
            ]
            Youtube().set_cookies(command)
            Youtube().set_language(command)
            Youtube().set_proxy(command)
            sd_url = w.worker(command).output()
            return redirect(sd_url.strip(), 301)
        else:
            direct_stream_cache[stream_cache_key] = filtered_content
            _save_direct_stream_to_disk(youtube_id, filtered_content)
            _prewarm_direct_neighbors(youtube_id)
            return _make_direct_response(filtered_content)
    else:
        s_youtube_id = youtube_id.split('-audio')[0]
        audio_cache_key = f"{stream_cache_key}:audio"
        cached_audio_url = direct_stream_cache.get(audio_cache_key)
        if cached_audio_url:
            return redirect(cached_audio_url, 301)

        command = [
            'yt-dlp',
            '-f', 'bestaudio',
            '--get-url',
            '--no-playlist',
            '--no-warnings',
            f'https://www.youtube.com/watch?v={s_youtube_id}'
        ]
        Youtube().set_cookies(command)
        Youtube().set_language(command)
        Youtube().set_proxy(command)
        audio_url = w.worker(command).output()
        direct_stream_cache[audio_cache_key] = audio_url.strip()
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
        vtt_text = _fix_vtt_alignment(response.text)
        flask_response = Response(vtt_text, mimetype='text/vtt')
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
            command = ['yt-dlp', '--no-warnings', '-o', '-', '-f', _get_video_format_selector('bestvideo+bestaudio'), '--sponsorblock-remove',  config['sponsorblock_cats'], '--restrict-filenames']
        else:
            command = ['yt-dlp', '--no-warnings', '-o', '-', '-f', _get_video_format_selector('best'), '--restrict-filenames']

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