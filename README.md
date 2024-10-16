# ytdlp2STRM
<a href="https://www.buymeacoffee.com/fe80grau" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" style="width: 120px !important;" ></a>

* Youtube / Twitch / ~~Crunchyroll~~ etc. to STRM files
* Watch Youtube through Jellyfin or Emby 
* Watch Twitch through Jellyfin or Emby 
* ~~Watch Crunchyroll through Jellyfin or Emby~~ https://github.com/fe80Grau/ytdlp2STRM/issues/52
![ytdlp2STRM](https://github.com/fe80Grau/ytdlp2STRM/assets/6680464/cc31ee7c-5e4b-450b-9a3b-526f191d18d8)
![image](https://github.com/fe80Grau/ytdlp2STRM/assets/6680464/7bee7f75-2f8d-483d-ac7d-2e0250d96d32)


## Prerequisite
* Python 3 https://www.python.org/downloads/
* FFmpeg https://ffmpeg.org/

## Installation and usage
* To allocate ytdlp2STRM, I suggest using /opt/ in Linux or C:\ProgramData in Windows.

# Linux
* The next steps have been tested on Ubuntu 22.04 LTS. In terminal:
```console
cd /opt && git clone https://github.com/fe80Grau/ytdlp2STRM.git
```
* Install requierments.txt
```console
cd /opt/ytdlp2STRM && pip install -r requierments.txt
```
* Copy service file to system services folder
```console
sudo cp config/ytdlp2strm.service /etc/systemd/system/ytdlp2strm.service
```
* Enable service
```console
sudo systemctl enable ytdlp2strm.service
```
* Start service
```console
sudo systemctl start ytdlp2strm.service
```
* Check it
```console
sudo systemctl status ytdlp2strm.service
```
* Check GUI in browser
```console
http://localhost:5000/
```


# Windows
* The next steps have been tested on Windows 11 Pro 22H2. Using Powershell or Windows Terminal with Administrator privileges:
```console
cd C:\ProgramData; git clone https://github.com/fe80Grau/ytdlp2STRM.git;
```
* Install requierments.txt
```console
cd C:\ProgramData\ytdlp2STRM; pip install -r requierments.txt
```
* Create a task that is scheduled to run main.py at startup. If you plan to install ytdlp2STRM in a different folder than C:\ProgramData\ytdlp2STRM, edit ./config/MS-TASK-ytdlp2STRM.xml
```console
schtasks.exe /create /tn "ytdlp2STRM" /xml C:\ProgramData\ytdlp2STRM\config\MS-TASK-ytdlp2STRM.xml
```
* Run task
```console
schtasks.exe /run /tn "ytdlp2STRM"
```
* In case everything is working, these commands will return "Running"
```console
(Get-ScheduledTask | Where TaskName -eq ytdlp2STRM ).State
```
* Check the GUI in the browser.
```console
http://localhost:5000/
```

# Docker
To deploy this as a Docker container, follow these steps in the ytdlp2STRM root folder.

* Build Docker image. The default host port is 5005, to change it edit Dockerfile and change the env value of DOCKER_PORT with the same port that you will configure in the docker run command.
```console
docker build . -t "ytdlp2strm" 
```
* Create a volume to preserve data.
```console
docker create --name ytdlp2strm-data ytdlp2strm 
```
* Run the container with volume and mount D:\media (host folder for accessing strm files, change it as you prefer) in /media (container folder).
```console
docker run -p 5005:5000 --restart=always -d -v D:\media:/media --volumes-from ytdlp2strm-data --name ytdlp2STRM ytdlp2strm
```
* Check the GUI in the browser
```console
http://localhost:5005/
```

# Docker HUB
* https://hub.docker.com/r/fe80grau/ytdlp2strm
![image](https://github.com/fe80Grau/ytdlp2STRM/assets/6680464/2375b8ad-62d3-41fd-baf3-e6b9dac0413d)

* * Run container. To persist strm files, you must configure a volume, that is, a directory on the host that points to the /media directory in the container. Also, the default env value of DOCKER_PORT is 5005, make sure to put 5005 as host port or re-declare the env value of DOCKER_PORT like I do in the following screenshot.
![image](https://github.com/fe80Grau/ytdlp2STRM/assets/6680464/2dd73f50-8347-48a1-a6cd-3c2266475c4d)

* Check the GUI in the browser
```console
http://localhost:5001/
```

# Docker compose YAML template
* Thank you INPoppoRTUNE
* INPoppoRTUNE was here

```yaml
---
services:
 ytdlp2strm:
    image: fe80grau/ytdlp2strm
    container_name: ytdlp2STRM
    environment:
      - AM_I_IN_A_DOCKER_CONTAINER=Yes
      - DOCKER_PORT=5005
    volumes:
      - /local/path/to/media:/media
      - /local/path/to/channel_list.json:/opt/ytdlp2STRM/plugins/youtube/channel_list.json
      - /local/path/to/yt_config.json:/opt/ytdlp2STRM/plugins/youtube/config.json
      - /local/path/to/config.json:/opt/ytdlp2STRM/config/config.json
      - /local/path/to/crons.json:/opt/ytdlp2STRM/config/crons.json
      - ytdlp2strm-data:/opt/ytdlp2STRM
    ports:
      - 5005:5000
    restart: always
volumes:
  ytdlp2strm-data:
```

Where:
- `/local/path/to/media` is the local folder where the `.strm` file will be created
- `/local/path/to/config.json` is optional and will set your ytdlp2STRM general settings; formatted as [config.example.json](https://github.com/fe80Grau/ytdlp2STRM/blob/main/config/config.example.json)
- `/local/path/to/crons.json` is optional and will set your ytdlp2STRM cronjob settings; formatted as [crons.example.json](https://github.com/fe80Grau/ytdlp2STRM/blob/main/config/crons.example.json)
- `/local/path/to/channel_list.json` is optional and will set your Youtube channel list; formatted as [channel_list.example.json](https://github.com/fe80Grau/ytdlp2STRM/blob/main/plugins/youtube/channel_list.example.json)
- `/local/path/to/yt_config.json` is optional and will set your Youtube plugin settings; formatted as [config.example.json](https://github.com/fe80Grau/ytdlp2STRM/blob/main/plugins/youtube/config.example.json)

* The default env value of DOCKER_PORT is 5005, make sure to put 5005 as host port or re-declare the env value of DOCKER_PORT


# Additional info
* After that you can view all channels folders within /media/Youtube and their strm files. If you are using Jellyfin/Emby, add /media/Youtube, /media/Twitch ~~and /media/Crunchyroll~~ as folders in Library and enjoy it!

## Youtube
* SponsorBlock doesn't work in redirect mode.
* Local NFO for each video
* audio- prefix

## Twitch
* If a live video is on air the !000-live-channel.strm will be created. The script will download the strm for each video in the /videos channel tab in any manner. Take a look at the limits and daterange values for videos in ./plugins/twitch/config.json.
* SponsorBlock doesn't work in redirect mode, Twitch only works in direct mode at the moment.

## TV3
* Plugin for 3cat, content in Catalan.

## ~~Crunchyroll~~
* ~~Requieres a cookie file from Premium user login (you can extract the cookie file from Crunchyroll with browser extension like https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc) or load a fresh cookie from browser (check discusion in https://github.com/yt-dlp/yt-dlp/issues/7442#issuecomment-1685036245).~~
* ~~Requires yt-dlp nightly build to work. `yt-dlp >=2024.05.22.232749.dev0`~~
* ~~Only works with login auth.~~
* ~~I'm using a filter language *your crunchyroll_audio_language config value* and extractor crunchyrollbeta:hardsub=*your crunchyroll_subtitle_language config value* to get a version with one language and subs embedded~~
* ~~To avoid constant rewriting of the strm files, a file called last_episode.txt is generated in the series directory, it contains the playlist position of the last strm downloaded, this will only generate strm for new episodes.~~
* ~~Patch yt-dlp if Crunchyroll not works https://github.com/yt-dlp/yt-dlp/issues/7442#issuecomment-1637748442~~
* ~~`mutate_values.json` A particular file for this plugin. Overwrites the value of a specified field. For example, in cases where the season given by yt-dlp - season_number does not correspond to the actual season of the series. The available fields are as follows: season_number, season, episode_number, and episode.~~
* ~~direct mode. On Crunchyroll, the direct mode inherits the functionality of the download mode. ~~
* ~~bridge mode. Given the latest updates, it is necessary to obtain the audio and video streams separately, redirect their output, and remux both tracks to finally serve them over HTTP. Experimental, sometimes it may fail to start playback and you need to try playing it again. There is no timestamp and it is not possible to navigate through the video's timeline.~~
* ~~With download mode, the audio and video streams will be downloaded separately, and after downloading, they will be remuxed to finally serve a final video/mp4 file. The files will be downloaded to `./temp/` and their lifespan will be 24 hours. This is configurable in `config.json` -> `ytdlp2strm_temp_file_duration`. The Crunchyroll plugin in download mode will automatically download the latest discovered episode of each series declared in `channel_list.json`.~~
* ~~In the `config.json` file, and specifically for the Crunchyroll plugin, there are 4 parameters: `jellyfin_preload_last_episode`, `jellyfin_base_url`, `jellyfin_user_id`, and `jellyfin_api_key`. When configured with their correct values, they allow detecting if an episode is being played and pre-downloading the next one to achieve a seamless playback flow without interruptions.~~

## Pokemon TV _The Pokémon TV app and website are closing, and the service will end on March 28, 2024._
* Thank you https://github.com/seiya-dev 
* This doesn't need a channel_list.json file


## main.py 
A little script to serve yt-dlp video/audio as HTTP data throught Flask and dynamic URLs. We can use this dynamic URLs with youtube id video in url like http://127.0.0.1:5000/youtube/direct/FxCqhXVc9iY and open it with VLC or save it in .strm file (works in Jellyfin)

## cli.py  
* Controller that loads plugins functions, used in crons to manage strm files
* Build strms manually:
```console
cd /opt/ytdlp2STRM/ && python3 cli.py --media youtube --params direct
```
You can change --media value for another plugin

## config/config.json
* ytdlp2strm_host 
* ytdlp2strm_port
* ytdlp2strm_keep_old_strm
* ytdlp2strm_temp_file_duration

## config/crons.json
* Working with Schedule library (https://schedule.readthedocs.io/en/stable/examples.html)
* Do attribute needs a list with commands ["--media", "youtube", "--params", "direct"], replace youtube with your plugin name and direct with your prefered mode.
* Custom timezone for each cron

* direct : A simple redirect to final stream URL. (faster, no disk usage, sponsorblock not works)
* bridge : Remuxing on fly. (fast, no disk usage)
* download : First download full video then it's served. (slow, temp disk usage)
* With download mode, the files in the temp folder older than 24h will be deleted.

## plugins/*media*/config.json
* strm_output_folder
* channels_list_file
* days_dateafter
* videos_limit
* [YOUTUBE] sponsorblock
* [YOUTUBE] sponsorblock_cats
* [YOUTUBE]  ~~[CRUNCHYROLL]~~ proxy
* [YOUTUBE]  ~~[CRUNCHYROLL]~~ proxy_url
* [YOUTUBE] cookies *Required to obtain the manifest for age-protected videos. It can be (cookies-from-browser or cookies)
* [YOUTUBE] cookie_value *If you set cookies as browser cookies you must indicate the browser (chrome, firefox, edge etc.). In the case of cookies, you must indicate the cookie file path stored in text format
* ~~[CRUNCHYROLL] crunchyroll_auth (~~browser, cookies or~~ login), browser option in addition with background task opening firefox is the best way to keep unatended workflow.~~
* ~~[CRUNCHYROLL] crunchyroll_browser (set if your choice in curnchyroll_auth is browser) You can read more about this searching --cookies-from-browser in https://github.com/yt-dlp/yt-dlp~~
* ~~[CRUNCHYROLL] crunchyroll_useragent (set if your choice in curnchyroll_auth is browser) Needs the same user agent that your browser. If you search current user-agent in Google you can see your user-agent, copy it.~~
* ~~[CRUNCHYROLL] crunchyroll_username (set if your choice in curnchyroll_auth is login)~~
* ~~[CRUNCHYROLL] crunchyroll_password (set if your choice in curnchyroll_auth is login)~~
* ~~[CRUNCHYROLL] crunchyroll_cookies_file (set if your choice in curnchyroll_auth is cookies)~~
* ~~[CRUNCHYROLL] crunchyroll_audio_language~~
* ~~[CRUNCHYROLL] crunchyroll_subtitle_language <- embedded in video~~
* ~~[CRUNCHYROLL] jellyfin_preload (False by default, set True to preload the next episode while the current is playing in Jellyfin)~~
* ~~[CRUNCHYROLL] jellyfin_preload_last_episode (An @Floflo10 idea. False by default, set True to preloads the last episode at the time its strm is generated. Remember in 24h will be deleted from temp folder)~~
* ~~[CRUNCHYROLL] jellyfin_base_url (Your Jellyfin URL, without final slash)~~
* ~~[CRUNCHYROLL] jellyfin_user_id (Your Jellyfin user_id)~~
* ~~[CRUNCHYROLL] jellyfin_api_key (Your Jellyfin api_key)~~

## plugins/*media*/channel_list.json
* [YOUTUBE] With "keyword-" prefix you can search for a keyword and this script will create the folders of channels founds dinamically and put inside them the strm files for each video. See an exaple in channel_list.example.json
* [YOUTUBE] Playlist needs "list-" prefix before playlist id, you can see an exaple in channel_list.example.json
* [YOUTUBE] If you want to get livestream from /streams youtube channel tab you need to add a new channel in channel_list with /streams (Check an example in ./plugins/youtube/channel_list.example.json)
* [TWITCH] This script makes a NFO file (tvshow.nfo) for each youtube or twitch channel (to get name, description and images). *Description only works in Linux systems at the moment
* ~~[CRUNCHYROLL] Only support URL series (not episodes), the script will create a folder for each serie, and subfolders for each season, inside season folder the strm episodes files  will be created~~

## Service
* LINUX: ytdlp2strm.service example service to run main.py with systemctl. 
* WINDOWS: MS-TASK-ytdlp2STRM.xml example scheduled task with schtasks.

## Credits
[![GitHub - ShieldsIO](https://img.shields.io/badge/GitHub-ShieldsIO-42b983?logo=GitHub)](https://github.com/badges/shields)
[![GitHub - Flask](https://img.shields.io/badge/GitHub-Flask-0000ff?logo=GitHub)](https://github.com/pallets/flask)
[![GitHub - yt-dlp](https://img.shields.io/badge/GitHub-ytdlp-ff0000?logo=GitHub)](https://github.com/yt-dlp/yt-dlp)
[![GitHub - andreztz](https://img.shields.io/badge/GitHub-andreztz-ffc230?logo=GitHub)](https://gist.github.com/andreztz/9e472fa6daa17d2f954958fc33e5a296)

