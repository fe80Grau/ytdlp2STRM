from flask import redirect
from sanitize_filename import sanitize
import os
from clases.config import config as c
from clases.worker import worker as w
from clases.folders import folders as f
from clases.nfo import nfo as n
import requests

## -- CRUNCHYROLL CLASS
class Crunchyroll:
    def __init__(self, channel=False):
        if channel:
            self.channel = channel.replace("https://www.crunchyroll.com/","")
            self.channel_url = "https://www.crunchyroll.com/{}".format(self.channel)
            self.channel_folder = self.channel.split('/')[-1]
            self.last_episode_file = "{}/{}/{}.{}".format(
                media_folder, 
                sanitize(
                    "{}".format(
                        self.channel_folder
                    )
                ), 
                "last_episode", 
                "txt"
            )
            self.new_content = False
            self.last_episode = self.get_start_episode()
            self.videos = self.get_videos()
    
    def get_videos(self):
        command = [
            'yt-dlp', 
            '--print', '%(season_number)s;%(season)s;%(episode_number)s;%(episode)s;%(webpage_url)s;%(playlist_autonumber)s', 
            '--no-download',
            '--no-warnings',
            '--match-filter', 'language={}'.format(audio_language),
            '--extractor-args', 'crunchyrollbeta:hardsub={}'.format(subtitle_language),
            '{}'.format(self.channel_url)
        ]
        
        self.set_auth(command)
        self.set_proxy(command)
        self.set_start_episode(command)
        #print(' '.join(command))
        return w.worker(command).pipe() 

    def get_start_episode(self):
        last_episode = 0
        if not os.path.isfile(self.last_episode_file):
            self.new_content = True
            f.folders().write_file(self.last_episode_file, "0")
        else:
            with open(self.last_episode_file) as fl:
                last_episode = fl.readlines()
                fl.close()
            
            last_episode = last_episode[0]
        
        return last_episode

    def set_start_episode(self, command):
        if not self.new_content:
            next_episode = int(self.last_episode)
            if next_episode < 1:
                next_episode = 1
            command.append('--playlist-start')
            command.append('{}'.format(next_episode))

    def set_last_episode(self, playlist_count):
        if self.new_content:
            f.folders().write_file(
                self.last_episode_file, 
                playlist_count
            )
        else:
            #sum_episode = int(self.last_episode) + int(playlist_count)
            f.folders().write_file(
                self.last_episode_file,
                str(playlist_count)
            )

    def set_auth(self, command, quotes=False):
        if config['crunchyroll_auth'] == "browser":
            command.append('--cookies-from-browser')
            if quotes:
                command.append(
                    '"{}"'.format(
                        config['crunchyroll_browser']
                    )
                )
            else:
                command.append(config['crunchyroll_browser'])

        if config['crunchyroll_auth'] == "cookies":
            command.append('--cookies')
            command.append(config['crunchyroll_cookies_file'])

        if config['crunchyroll_auth'] == "login":
            command.append('--username')
            command.append(config['crunchyroll_username'])
            command.append('--password')
            command.append(config['crunchyroll_password'])

        command.append('--user-agent')
        if quotes:
            command.append(
                '"{}"'.format(
                    config['crunchyroll_useragent']
                )
            )
        else:
            command.append(
                '{}'.format(
                    config['crunchyroll_useragent']
                )
            )

    def set_proxy(self, command):
        if proxy:
            if proxy_url != "":
                command.append('--proxy')
                command.append(proxy_url)

## -- END

## -- LOAD CONFIG AND CHANNELS FILES
ytdlp2strm_config = c.config(
    './config/config.json'
).get_config()

config = c.config(
    './plugins/crunchyroll/config.json'
).get_config()

channels = c.config(
    config["channels_list_file"]
).get_channels()

source_platform = "crunchyroll"
media_folder = config["strm_output_folder"]
channels_list = config["channels_list_file"]
cookies_file = config["crunchyroll_cookies_file"]
subtitle_language = config["crunchyroll_subtitle_language"]
audio_language = config['crunchyroll_audio_language']
if 'proxy' in config:
    proxy = config['proxy']
    proxy_url = config['proxy_url']
else:
    proxy = False
    proxy_url = ""
## -- END

## -- MANDATORY TO_STRM FUNCTION 
def to_strm(method):
    for crunchyroll_channel in channels:
        print("Preparing channel {}".format(crunchyroll_channel))

        crunchyroll = Crunchyroll(crunchyroll_channel)
        #crunchyroll.get_cookie_from_firefox()

        # -- MAKES CHANNEL DIR (AND SUBDIRS) IF NOT EXIST, REMOVE ALL STRM IF KEEP_OLDER_STRM IS SETTED TO FALSE IN GENERAL CONFIG
        f.folders().make_clean_folder(
            "{}/{}".format(
                media_folder,  
                sanitize(
                    "{}".format(
                        crunchyroll.channel_folder
                    )
                )
            ),
            False,
            config
        )
        ## -- END

        # -- BUILD STRM
        process = crunchyroll.videos

        try:
            for line in iter(process.stdout.readline, b''):
                if line != "" and not 'ERROR' in line and not 'WARNING' in line:
                    #print(line)
                    season_number = str(line).rstrip().split(';')[0].zfill(2)
                    season = str(line).rstrip().split(';')[1]
                    episode_number = (line).rstrip().split(';')[2].zfill(4)
                    episode = (line).rstrip().split(';')[3]
                    url = (line).rstrip().split(';')[4].replace(
                        'https://www.crunchyroll.com/',
                        ''
                    ).replace('/','_')
                    playlist_count = (line).rstrip().split(';')[5]
               
                    video_name = "{} - {}".format(
                        "S{}E{}".format(
                            season_number, 
                            episode_number
                        ), 
                        episode
                    )

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
                                crunchyroll.channel_folder
                            )
                        ),  
                        sanitize(
                            "S{} - {}".format(
                                season_number, 
                                season
                            )
                        ), 
                        sanitize(video_name), 
                        "strm"
                    )

                    f.folders().make_clean_folder(
                        "{}/{}/{}".format(
                            media_folder,  
                            sanitize(
                                "{}".format(
                                    crunchyroll.channel_folder
                                )
                            ),  
                            sanitize(
                                "S{} - {}".format(
                                    season_number, 
                                    season
                                )
                            )
                        ),
                        False,
                        config
                    )

                    if not os.path.isfile(file_path):
                        f.folders().write_file(
                            file_path, 
                            file_content
                        )

                    if crunchyroll.new_content:
                        crunchyroll.set_last_episode(playlist_count)
                    else:
                        #print(int(playlist_count))
                        sum_episode = int(crunchyroll.last_episode) + int(playlist_count)
                        #print(int(crunchyroll.last_episode))
                        #print(sum_episode)
                        crunchyroll.set_last_episode(
                            str(sum_episode)
                        )

                if not line: break
                
        finally:
            process.kill()
        ## -- END
    return True 
## -- END

## -- EXTRACT / REDIRECT VIDEO DATA 
def direct(crunchyroll_id): 
    command = [
        'yt-dlp', 
        '-f', 'best',
        '--no-warnings',
        '--match-filter', '"language={}"'.format(audio_language),
        '--extractor-args', '"crunchyrollbeta:hardsub={}"'.format(subtitle_language),
        'https://www.crunchyroll.com/{}'.format(crunchyroll_id.replace('_','/')),
        '--get-url'
    ]
    Crunchyroll().set_auth(command,True)
    Crunchyroll().set_proxy(command)
    crunchyroll_url = w.worker(command).output()
    return redirect(crunchyroll_url, code=301)
## -- END