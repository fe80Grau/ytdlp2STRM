# ytdlp2STRM
* Youtube / Twitch / Crunchyroll etc. to STRM files
* Watch Youtube through Jellyfin or Emby 
* Watch Twitch through Jellyfin or Emby 
* Watch Crunchyroll through Jellyfin or Emby 
![ytdlp2STRM](https://github.com/fe80Grau/ytdlp2STRM/assets/6680464/cc31ee7c-5e4b-450b-9a3b-526f191d18d8)
![Captura de pantalla 2023-09-06 170858](https://github.com/fe80Grau/ytdlp2STRM/assets/6680464/d3fa6b5a-ca75-4dc3-b9e6-354ddf9b1fdf)

<a href="https://www.buymeacoffee.com/fe80grau" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" style="width: 120px !important;" ></a>

## Prerequisite
* Python 3 https://www.python.org/downloads/

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

* Build Docker image 
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

# Additional info
* After that you can view all channels folders within /media/Youtube and their strm files. If you are using Jellyfin/Emby, add /media/Youtube, /media/Twitch and /media/Crunchyroll as folders in Library and enjoy it!

## Youtube
* SponsorBlock doesn't work in redirect mode.
* Local NFO for each video

## Twitch
* If a live video is on air the !000-live-channel.strm will be created. The script will download the strm for each video in the /videos channel tab in any manner. Take a look at the limits and daterange values for videos in ./plugins/twitch/config.json.
* SponsorBlock doesn't work in redirect mode, Twitch only works in direct mode at the moment.

## Crunchyroll
* Requieres a cookie file from Premium user login (you can extract the cookie file from Crunchyroll with browser extension like https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc) or load a fresh cookie from browser (check discusion in https://github.com/yt-dlp/yt-dlp/issues/7442#issuecomment-1685036245).
* I'm using a filter language *your crunchyroll_audio_language config value* and extractor crunchyrollbeta:hardsub=*your crunchyroll_subtitle_language config value* to get a version with one language and subs embedded
* To avoid constant rewriting of the strm files, a file called last_episode.txt is generated in the series directory, it contains the playlist position of the last strm downloaded, this will only generate strm for new episodes.
* Patch yt-dlp if Crunchyroll not works https://github.com/yt-dlp/yt-dlp/issues/7442#issuecomment-1637748442

## Pokemon TV 
* Thank you https://github.com/seiya-dev 
* This doesn't need a channel_list.json file

## SX3 - Anime en Català (Catalan Anime)
* Last mp4 url only works if it's requested from Spain IP. This plugin have http_get_proxy and http_get_proxy_url to set an http get proxy , for example http://proxy/?address=

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

## config/crons.json
* Working with Schedule library (https://schedule.readthedocs.io/en/stable/examples.html)
* Do attribute needs a list with commands ["--media", "youtube", "--params", "direct"], replace youtube with your plugin name and direct with your prefered mode.

* direct : A simple redirect to final stream URL. (faster, no disk usage, sponsorblock not works)
* bridge : Remuxing on fly. (fast, no disk usage)
* download : First download full video then it's served. (slow, temp disk usage)

## plugins/*media*/config.json
* strm_output_folder
* channels_list_file
* days_dateafter
* videos_limit
* [YOUTUBE] sponsorblock
* [YOUTUBE] sponsorblock_cats
* [YOUTUBE] [CRUNCHYROLL] proxy
* [YOUTUBE] [CRUNCHYROLL] proxy_url
* [CRUNCHYROLL] crunchyroll_auth (browser, cookies or login), browser option in addition with background task opening firefox is the best way to keep unatended workflow.
* [CRUNCHYROLL] crunchyroll_browser (set if your choice in curnchyroll_auth is browser) You can read more about this searching --cookies-from-browser in https://github.com/yt-dlp/yt-dlp
* [CRUNCHYROLL] crunchyroll_useragent (set if your choice in curnchyroll_auth is browser) Needs the same user agent that your browser. If you search current user-agent in Google you can see your user-agent, copy it.
* [CRUNCHYROLL] crunchyroll_username (set if your choice in curnchyroll_auth is login)
* [CRUNCHYROLL] crunchyroll_password (set if your choice in curnchyroll_auth is login)
* [CRUNCHYROLL] crunchyroll_cookies_file (set if your choice in curnchyroll_auth is cookies)
* [CRUNCHYROLL] crunchyroll_audio_language
* [CRUNCHYROLL] crunchyroll_subtitle_language <- embedded in video
* [SX3] http_get_proxy
* [SX3] http_get_proxy_url

## plugins/*media*/channel_list.json
* [YOUTUBE] With "keyword-" prefix you can search for a keyword and this script will create the folders of channels founds dinamically and put inside them the strm files for each video. See an exaple in channel_list.example.json
* [YOUTUBE] Playlist needs "list-" prefix before playlist id, you can see an exaple in channel_list.example.json
* [YOUTUBE] If you want to get livestream from /streams youtube channel tab you need to add a new channel in channel_list with /streams (Check an example in ./plugins/youtube/channel_list.example.json)
* [TWITCH] This script makes a NFO file (tvshow.nfo) for each youtube or twitch channel (to get name, description and images). *Description only works in Linux systems at the moment
* [CRUNCHYROLL] Only support URL series (not episodes), the script will create a folder for each serie, and subfolders for each season, inside season folder the strm episodes files  will be created 

## Service
* LINUX: ytdlp2strm.service example service to run main.py with systemctl. 
* WINDOWS: MS-TASK-ytdlp2STRM.xml example scheduled task with schtasks.

## Pendings
* Include subtitles
* Video quality. Config options: Forced (worst, balanced, best) or Dynamic (depends connection speed)
* Get Youtube account subscrition channel list
* Do this as a Jellyfin plugin with GUI (settings and search for channels to add in list)

## Credits
[![GitHub - ShieldsIO](https://img.shields.io/badge/GitHub-ShieldsIO-42b983?logo=GitHub)](https://github.com/badges/shields)
[![GitHub - Flask](https://img.shields.io/badge/GitHub-Flask-0000ff?logo=GitHub)](https://github.com/pallets/flask)
[![GitHub - yt-dlp](https://img.shields.io/badge/GitHub-ytdlp-ff0000?logo=GitHub)](https://github.com/yt-dlp/yt-dlp)
[![GitHub - andreztz](https://img.shields.io/badge/GitHub-andreztz-ffc230?logo=GitHub)](https://gist.github.com/andreztz/9e472fa6daa17d2f954958fc33e5a296)

