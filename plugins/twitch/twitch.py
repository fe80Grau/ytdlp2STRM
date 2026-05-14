from flask import stream_with_context, Response, send_file, redirect
from utils.sanitize import sanitize
import os
import requests
import re
from utils.episode_numbering import format_episode_title
import time
import sys
from datetime import datetime
from cachetools import TTLCache
from clases.config import config as c
from clases.worker import worker as w
from clases.folders import folders as f
from clases.nfo import nfo as n
from clases.log import log as l
from clases.jellyfin_notifier.jellyfin_notifier import JellyfinNotifier


## -- TWITCH CLASS
class Twitch:
    def __init__(self, channel):
        self.channel = channel
        self.twitch_channel_url = "https://www.twitch.tv/{}".format(channel)
        self.channel_name = self.get_name()
        self.images = self.get_thumbs()
        self.direct = self.get_direct()
        self.videos = self.get_videos()
    
    def set_cookies(self, command):
        if cookies and cookie_value and cookies.strip() and cookie_value.strip():
            command.append(f'--{cookies}')
            command.append(cookie_value)

    def get_name(self):
        l.log("twitch", f"Getting name for channel: {self.channel}")
        command = [
            'yt-dlp', 
            'https://www.twitch.tv/{}/videos'.format(
                self.channel
            ), 
            '--print', '%(uploader)s', 
            '--playlist-items', '1',
            '--restrict-filenames',
            '--ignore-errors',
            '--no-warnings',
            '--compat-options', 'no-youtube-channel-redirect',
            '--no-warnings'
        ]
        
        self.set_cookies(command)
        #l.log("twitch", f"Executing command: {' '.join(command)}")

        channel_name = w.worker(
            command
        ).output().strip().replace('"', '')
        
        l.log("twitch", f"Got channel name: {channel_name}")
        
        if 'ERROR' in channel_name or not channel_name.strip():
            channel_name = self.channel
        
        return channel_name

    def get_direct(self):
        #Get current livestream
        l.log("twitch", "Getting direct stream (live)")
        command = [
            'yt-dlp', 
            '--print', '"%(id)s;%(title)s;%(description)s;%(thumbnail)s;%(upload_date)s"', 
            '--ignore-errors',
            '--no-warnings',
            '{}'.format(
                self.twitch_channel_url
            )
        ]
        
        self.set_cookies(command)

        result = w.worker(command).output()
        l.log("twitch", f"Direct stream result obtained")
        return [result]


    def get_pictures(self):
        headers = {
            'Accept': '*/*',
            'Client-Id': '{}'.format(client_id),
            'Client-Version': '{}'.format(client_version),
            'Connection': 'keep-alive',
            'Content-Type': 'text/plain;charset=UTF-8',
            'Origin': 'https://www.twitch.tv',
            'Referer': 'https://www.twitch.tv/',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site',
        }
        data = [
            {
                "operationName":"ChannelShell",
                "variables":{
                    "login":"{}".format(
                        self.channel
                    )
                },
                "extensions":{
                    "persistedQuery":{
                        "versions":1,
                        "sha256Hash":"{}".format(
                            sha256_channelShell
                        )
                    }
                }
            }
        ]

        response = requests.post(
            'https://gql.twitch.tv/gql', 
            headers=headers, 
            json=data
        )

        return response.json()
    
    def get_thumbs(self):
        #Table thumbnails
        l.log("twitch", f"Getting thumbnails for channel: {self.channel}")
        c = 0
        command = [
            'yt-dlp', 
            'https://www.twitch.tv/{}/{}'.format(
                self.channel,"videos"
            ),
            '--list-thumbnails',
            '--restrict-filenames',
            '--ignore-errors',
            '--no-warnings',
            '--no-download',
            '--playlist-items', '1'
        ]
        
        # No agregar cookies para thumbnails (son públicas)
        # self.set_cookies(command)
        l.log("twitch", f"Executing thumbnails command")
        #The madness begins... 
        #No comments between lines, smoke a joint if you want understand it
        lines = w.worker(
            command
        ).output().split('\n')
        headers = []
        thumbnails = []
        for line in lines:
            line = ' '.join(line.split())
            if not '[' in line and not 'has no' in line:
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
        #finally...
        l.log("twitch", f"Thumbnails processed, found {len(thumbnails)} thumbnails")

        preview = ""
        try:
            url_avatar_uncropped_index = next((index for (index, d) in enumerate(thumbnails) if d["ID"] == "0"), None)
            preview = thumbnails[url_avatar_uncropped_index]['URL'].replace(
                '320x180',
                '1920x1080'
            )
        except:
            log_text = ("No poster detected")
            l.log("twitch", log_text)
        
        l.log("twitch", f"Getting pictures from Twitch API")
        pictures = self.get_pictures()
        l.log("twitch", f"Pictures obtained")
        poster = ""
        landscape = ""

        for picture in pictures:
            poster = picture['data']['userOrError']['profileImageURL'].replace(
                '70x70',
                '300x300'
            )
            landscape = picture['data']['userOrError']['bannerImageURL']

        return {
            "poster" : poster,
            "landscape" : landscape,
            "preview" : preview
        }

    def get_videos(self):
        l.log("twitch", f"Getting videos for channel")
        command = [
            'yt-dlp', 
            '--print', '"%(id)s;%(title)s;%(description)s;%(thumbnail)s;%(upload_date)s"', 
            '--dateafter', "today-{}days".format(days_after),
            '--playlist-start', '1', 
            '--playlist-end', videos_limit, 
            '--ignore-errors',
            '--no-warnings',
            '{}/{}'.format(
                self.twitch_channel_url,
                "videos"
            )
        ]
        
        self.set_cookies(command)
        
        result = w.worker(command).output().split('\n')
        l.log("twitch", f"Got {len(result)} video entries")
        return result
## -- END

recent_requests = TTLCache(maxsize=200, ttl=30)

## -- LOAD CONFIG AND CHANNELS FILES
ytdlp2strm_config = c.config(
    './config/config.json'
).get_config()

config = c.config(
    './plugins/twitch/config.json'
).get_config()

channels = c.config(
    config["channels_list_file"]
).get_channels()

media_folder = config["strm_output_folder"]
channels_list = config["channels_list_file"]
source_platform = "twitch"
sha256_channelShell = "580ab410bcd0c1ad194224957ae2241e5d252b2c5173d8e0cce9d32d5bb14efe"
client_id = "kimne78kx3ncx6brgo4mv6wki5h1ko"
client_version = "21e5a00f-b4e2-4fe7-a6a1-13de6e72e9b1"

if 'days_dateafter' in config:
    days_after = config["days_dateafter"]
    videos_limit = config['videos_limit']
else:
    days_after = "10"
    videos_limit = "10"

try:
    cookies = config["cookies"]
    cookie_value = config["cookie_value"]
except:
    cookies = ''
    cookie_value = ''

try:
    episode_format = config["episode_format"]
except:
    episode_format = 'sequential'

try:
    video_quality = str(config["video_quality"]).strip().lower()
except:
    video_quality = "best"

def get_video_quality_height():
    if not video_quality or video_quality in ("best", "0", "none", "default"):
        return None
    match = re.search(r'\d+', video_quality)
    if not match:
        return None
    return int(match.group(0))

def get_video_format_selector(default_selector='best'):
    max_height = get_video_quality_height()
    if not max_height:
        return default_selector
    return f'bestvideo[height<={max_height}]+bestaudio/best[height<={max_height}]/best'

# Función helper para agregar cookies a comandos
def set_cookies_to_command(command):
    if cookies and cookie_value and cookies.strip() and cookie_value.strip():
        command.append(f'--{cookies}')
        command.append(cookie_value)

## -- END


def video_id_exists_in_content(media_folder, video_id):
    for root, dirs, files in os.walk(media_folder):
        for file in files:
            if file.endswith(".strm"):
                file_path = os.path.join(root, file)
                with open(file_path, 'r') as f:
                    if video_id in f.read():
                        return True
    return False

def parse_twitch_metadata_line(line, twitch_channel, source):
    line = str(line).strip()
    if not line or 'ERROR' in line:
        return None

    line = line.replace('"', '')
    parts = line.rstrip().split(';')
    if len(parts) < 5:
        l.log("twitch", f"Skipping malformed {source} metadata for {twitch_channel}: expected 5 fields, got {len(parts)}")
        return None

    try:
        date = datetime.strptime(parts[4], '%Y%m%d')
    except ValueError:
        l.log("twitch", f"Skipping malformed {source} metadata for {twitch_channel}: invalid upload date '{parts[4]}'")
        return None

    description = parts[2]
    if description == "NA":
        description = ""

    return {
        "video_id": parts[0],
        "video_name": parts[1],
        "description": description,
        "thumbnail": parts[3],
        "upload_date": date.strftime('%Y-%m-%d'),
        "year": date.year
    }

## -- MANDATORY TO_STRM FUNCTION 
def to_strm(method):
    for twitch_channel in channels:
        log_text = ("Preparing channel {}".format(twitch_channel))
        l.log("twitch", log_text)
        twitch_channel = twitch_channel.replace('https://www.twitch.tv/', '')
        twitch = Twitch(twitch_channel)

        # -- MAKES CHANNEL DIR IF NOT EXIST,
        f.folders().make_clean_folder(
            "{}/{}".format(
                media_folder,  
                sanitize(
                    "{}".format(
                        twitch.channel
                    )
                )
            ),
            False,
            ytdlp2strm_config
        )
        ## -- END
        # -- MAKES CHANNEL DIR IF NOT EXIST,
        f.folders().make_clean_folder(
            "{}/{}".format(
                media_folder,  
                sanitize(
                    "{}".format(
                        twitch.channel
                    )
                )
            ),
            False,
            ytdlp2strm_config
        )
        ## -- END

        ## -- BUILD CHANNEL NFO FILE
        n.nfo(
            "tvshow",
            "{}/{}".format(
                media_folder, 
                "{}".format(
                    twitch.channel
                )
            ),
            {
                "title" : twitch.channel_name,
                "plot" : "",
                "landscape" : twitch.images['landscape'],
                "poster" : twitch.images['poster'],
                "studio" : "Twitch"
            }
        ).make_nfo()
        ## -- END 
        
        ## -- GET ON AIR STREAMING
        for line in twitch.direct:
            file_path = "{}/{}/{}.{}".format(
                media_folder,  
                sanitize(
                    "{}".format(
                        twitch_channel)
                    ), 
                sanitize(
                    "!000-live-{}".format(
                        twitch_channel
                    )
                ), 
                "strm"
            )
            if line != "":
                metadata = parse_twitch_metadata_line(line, twitch_channel, "direct")
                if metadata:
                    video_id = metadata["video_id"]
                    video_name = metadata["video_name"]
                    description = metadata["description"]
                    thumbnail = metadata["thumbnail"]
                    try:
                        video_name.pop(3)
                    except:
                        pass

                    video_name = "{} [{}]".format(
                        ' '.join(
                            video_name
                        ),
                        video_id
                    )

                    file_content = "http://{}:{}/{}/{}/{}".format(
                        ytdlp2strm_config['ytdlp2strm_host'], 
                        ytdlp2strm_config['ytdlp2strm_port'], 
                        source_platform, 
                        method, "{}@{}".format(
                            twitch_channel, 
                            video_id
                            )
                        )

                    data = {
                        "video_id" : video_id, 
                        "video_name" : video_name
                    }

                    if not os.path.isfile(file_path):
                        f.folders().write_file(
                            file_path, 
                            file_content
                        )
                    ## -- BUILD VIDEO NFO FILE
                    n.nfo(
                        "episode",
                        "{}/{}".format(
                            media_folder, 
                            "{}".format(
                                twitch.channel
                            )
                        ),
                        {
                            "item_name" : sanitize(
                                "!000-live-{}".format(
                                    twitch.channel
                                )
                            ),
                            "title" : sanitize(f'!000-live-{video_name}'),
                            "upload_date" : "",
                            "year" : "",
                            "plot" : description.replace('\n', ' <br/>\n '),
                            "season" : "1",
                            "episode" : "",
                            "preview" : thumbnail
                        }
                    ).make_nfo()
                    ## -- END 
            else:
                log_text = ("The channel is not currently live")
                l.log("twitch", log_text)
                try:
                    os.remove( file_path )
                    os.remove( file_path.replace('.strm','.nfo'))
                    os.remove( file_path.replace('.strm','.png'))
                except:
                    pass
        ## -- END

        ## -- GET VIDEOS TAB
        # Reverse video list so oldest videos get lower episode numbers
        reversed_videos = list(reversed(twitch.videos))
        for line in reversed_videos:
            if line != "":
                metadata = parse_twitch_metadata_line(line, twitch_channel, "videos")
                if metadata:
                    video_id = metadata["video_id"]
                    video_name = metadata["video_name"].split(" ")
                    description = metadata["description"]
                    thumbnail = metadata["thumbnail"]
                    upload_date = metadata["upload_date"]
                    year = metadata["year"]
                    try:
                        video_name.pop(3)
                    except:
                        pass

                    video_name = ' '.join(
                        video_name
                    )
                    video_name = re.sub(r'\d{4}-\d{2}-\d{2} \d{4}', '', video_name).strip()
                    video_name = "{} [{}]".format(
                        video_name,
                        video_id
                    )

                    file_content = "http://{}:{}/{}/{}/{}".format(
                        ytdlp2strm_config['ytdlp2strm_host'], 
                        ytdlp2strm_config['ytdlp2strm_port'], 
                        source_platform,
                        method, 
                        "{}@{}".format(
                            twitch_channel, 
                            video_id
                        )
                    )

                    channel_folder = sanitize(
                        "{}".format(
                            twitch.channel
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
                            "{}".format(
                                twitch_channel
                            )
                        )
                    )

                    if video_id_exists_in_content(folder_path, video_id):
                        l.log("twitch", f'Video {video_id} already exists')
                        continue

                    data = {
                        "video_id" : video_id, 
                        "video_name" : video_name
                    }
                    
                    # Create season folder if it doesn't exist (BEFORE creating NFO)
                    season_folder_path = "{}/{}/{}".format(media_folder, channel_folder, season_folder)
                    if not os.path.exists(season_folder_path):
                        os.makedirs(season_folder_path, exist_ok=True)

                    ## -- BUILD VIDEO NFO FILE
                    n.nfo(
                        "episode",
                        "{}/{}/{}".format(
                            media_folder, 
                            "{}".format(
                                twitch.channel
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
        
        # Notify Jellyfin/Emby after processing all videos for this channel
        jellyfin_notifier = JellyfinNotifier(config)
        if jellyfin_notifier.enabled:
            jellyfin_notifier.notify_new_content(f"{media_folder}/{sanitize(twitch.channel)}")
        ## --END
    
    return True 
## -- END

## --  REDIRECT VIDEO DATA 
def direct(twitch_id, remote_addr): 
    current_time = time.time()
    cache_key = f"{remote_addr}_{twitch_id}"
    
    # Check if the request is already cached
    if cache_key not in recent_requests:
        log_text = f'[{remote_addr}] Playing {twitch_id}'
        l.log("twitch", log_text)
        recent_requests[cache_key] = current_time

    channel = twitch_id.split("@")[0]
    video_id = twitch_id.split("@")[1]
    command = [
        'yt-dlp', 
        '-f', get_video_format_selector('best'),
        '--no-warnings',
        f'https://www.twitch.tv/videos/{video_id}',
        '--get-url'
    ]
    set_cookies_to_command(command)

    twitch_url = w.worker(command).output()

    if 'ERROR' in twitch_url or not twitch_url:
        command_retry = [
            'yt-dlp', 
            '-f', get_video_format_selector('best'),
            '--no-warnings',
            f'https://www.twitch.tv/videos/{video_id.replace("v", "")}',
            '--get-url'
        ]
        set_cookies_to_command(command_retry)
        twitch_url = w.worker(command_retry).output()

        if 'ERROR' in twitch_url or not twitch_url:
            command_live = [
                'yt-dlp', 
                '-f', get_video_format_selector('best'),
                '--no-warnings',
                f'https://www.twitch.tv/{channel}',
                '--get-url'
            ]
            set_cookies_to_command(command_live)
            twitch_url = w.worker(command_live).output()

    twitch_url = twitch_url.strip()
    return redirect(twitch_url, code=301)

def bridge(twitch_id):
    channel = twitch_id.split("@")[0]
    video_id = twitch_id.split("@")[1]

    turl = 'https://www.twitch.tv/videos/{}'.format(
        video_id
    )
    command = [
        'yt-dlp', 
        '-f', get_video_format_selector('best'),
        '--no-warnings',
        turl,
        '--get-url'
    ]
    set_cookies_to_command(command)
    twitch_url = w.worker(command).output()

    if 'ERROR' in twitch_url:

        turl = 'https://www.twitch.tv/videos/{}'.format(
            video_id.replace(
                'v',
                ''
            )
        )

        command_retry = [
            'yt-dlp', 
            '-f', get_video_format_selector('best'),
            '--no-warnings',
            turl,
            '--get-url'
        ]
        set_cookies_to_command(command_retry)
        twitch_url = w.worker(command_retry).output()

        if 'ERROR' in twitch_url:

            turl = 'https://www.twitch.tv/{}'.format(
                channel          
            )

            command_live = [
                'yt-dlp', 
                '-f', get_video_format_selector('best'),
                '--no-warnings',
                'https://www.twitch.tv/{}'.format(
                    channel          
                ),
                '--get-url'
            ]
            set_cookies_to_command(command_live)
            twitch_url = w.worker(command_live).output()



    def generate():
        startTime = time.time()
        buffer = []
        sentBurst = False
        command = [
            'yt-dlp', 
            '-o', '-',
            '-f', get_video_format_selector('best'),
            '--no-warnings',
            '--restrict-filenames',
            turl
        ]

        set_cookies_to_command(command)
        
        process = w.worker(command).pipe()
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
                        log_text = ("Send initial burst #", i)
                        l.log("twitch", log_text)
                        yield buffer.pop(0)

                elif time.time() > startTime + 3 and len(buffer) > 0:
                    yield buffer.pop(0)

                process.poll()
                if isinstance(process.returncode, int):
                    if process.returncode > 0:
                        log_text = ('yt-dlp Error', process.returncode)
                        l.log("twitch", log_text)
                    break
        finally:
            process.kill()

    return Response(
        stream_with_context(generate()), 
        mimetype = "video/mp4"
    ) 


## -- END