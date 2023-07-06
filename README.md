# ytdlp2STRM
* Youtube / Twitch / Crunchyroll to STRM files
* Watch Youtube / Twitch / Crunchyroll with Jellyfin/Emby 
* I recommend YoutubeMetadata plugin for Jellyfin
![ytdlp2STRM](https://github.com/fe80Grau/ytdlp2STRM/assets/6680464/cc31ee7c-5e4b-450b-9a3b-526f191d18d8)

## Requierments
* Python 3
* yt-dlp
* Flask

## Installation and usage
* I recommend /opt/ in Linux or C:\ProgramData in Windows, to allocate ytdlp2STRM.
* The next steps are tested over Ubuntu 22.04 LTS
```console
cd /opt && git clone https://github.com/fe80Grau/ytdlp2STRM.git
```
* Install requierments.txt
```console
cd /opt/ytdlp2STRM && pip install -r requierments.txt
```
* Create folder to store .strm files (by default /media/Youtube and /media/Twitch and /media/Crunchyroll)
```console
mkdir /media/Youtube
```
```console
mkdir /media/Twitch
```
```console
mkdir /media/Crunchyroll
```
* EDIT plugins/youtube/channel_list.example.json with your channels names (you can see channel name (or ID or USER)  after first / (slash) in youtube channel URL). Save it as channel_list.json (delete .example sufix).
* EDIT plugins/youtube/config.json with your preferences
* EDIT plugins/twitch/channel_list.example.json with your channels names (you can see channel name after first / (slash) in twitch channel URL). Save it as channel_list.json (delete .example sufix).
* EDIT plugins/twitch/config.json with your preferences
* EDIT plugins/crunchyroll/channel_list.example.json with your series URL path (you can see this  after first / (slash) in Crunchyroll URL). Save it as channel_list.json (delete .example sufix).
* EDIT plugins/crunchyroll/config.json with your preferences
* EDIT config/config.json [and ytdlp2strm.service with your preferences and copy ytdlp2strm.service to /etc/systemd/system]*Between brackets only Linux.
* You can leave the channel_list.json empty to "deactivate" the plugin. If you do this don't remove the square brackets, your file should look like this: []
* ytdlp2strm_keep_old_strm in config/config.json is true by default, this options keep in filesystem all strm files,  with false all strm will be cleaned in each ytdlp2strm execution
* I'm testing SponsorBlock. Requieres ffmpeg custom build from yt-dlp. https://github.com/yt-dlp/FFmpeg-Builds#ffmpeg-static-auto-builds (Download your version Linux x64 or LinuxARM64, Windows x64 or Windows x86), extract an replace binaries in bin folder in your system. Normaly ffmpeg, ffprobe and ffplay binaries are installed in /usr/bin/ , back up orginials before replace. 
* SponsorBlock is disabled by default in config.json
* SponsorBlock categories: sponsor, intro, outro, selfpromo, preview, filler, interaction, music_offtopic, poi_highlight, chapter, all. By default is setted sponsor.
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

## Youtube
* Example cron.d file to create strm files in **direct mode** from channel_list every 2 hours (duration info, no download/disk usage, fast first loading, no cpu usage, redirect to direct youtube url with video/audio merged, faster mode)
* SponsorBlock not works on redirect mode
> ``` console
> cd /etc/cron.d && sudo echo "0 */2 * * * root cd /opt/ytdlp2STRM && /usr/bin/python3 /opt/ytdlp2STRM/cli.py --media youtube --params direct" > ytdlp2STRM_youtube_direct
> ```
* Example cron.d file to create strm files in **download mode** from channel_list every 2 hours (cached mode, duration info, temp download/disk usage, slow first loading)
> ``` console
> cd /etc/cron.d && sudo echo "0 */2 * * * root cd /opt/ytdlp2STRM && /usr/bin/python3 /opt/ytdlp2STRM/cli.py --media youtube --params download" > ytdlp2STRM_youtube_download
> ```
* Example cron.d file to create strm files in **bridge mode** from channel_list every 2 hours (no duration info, no download/disk usage, fast first loading)
> ``` console
> cd /etc/cron.d && sudo echo "0 */2 * * * root cd /opt/ytdlp2STRM && /usr/bin/python3 /opt/ytdlp2STRM/cli.py --media youtube --params bridge" > ytdlp2STRM_youtube_bridge
> ```

* After that you can see all channels folders under /media/Youtube and strm files inside them. If you are using Jellyfin/Emby, add /media/Youtube, /media/Twitch and /media/Crunchyroll as folder in Library and enjoy it!

## Twitch

* Example cron.d file to create strm files in **direct mode** from channel_list every 10 minutes (duration info, no download/disk usage, fast first loading, no cpu usage, redirect to direct twitch url with video/audio merged, faster mode)
* If a live video is on air the !000-live-revenant.strm will be created. Any way the script will download strm for each video in /videos channel tab. See plugins/twitch/config.json videos limits and daterange values.
* SponsorBlock not works on redirect mode, Twitch only works over direct mode at the moment.
> ``` console
> cd /etc/cron.d && sudo echo "*/10 * * * * root cd /opt/ytdlp2STRM && /usr/bin/python3 /opt/ytdlp2STRM/cli.py --media twitch --params direct" > ytdlp2STRM_twitch_direct
> ```


## Crunchyroll

* Example cron.d file to create strm files in **direct mode** from channel_list every 24 hours (duration info, no download/disk usage, fast first loading, no cpu usage, redirect to direct twitch url with video/audio merged, faster mode)
* Requieres a cookie file from Premium user login (you can extract the cookie file from Crunchyroll with browser extension like https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)
* I'm using a filter language *your crunchyroll_audio_language config value* and extractor crunchyrollbeta:hardsub=*your crunchyroll_subtitle_language config value* to get a version with one language and subs embedded
* To avoid constant rewriting of the strm files, a file called last_episode.txt is generated in the series directory, it contains the playlist position of the last strm downloaded, this will only generate strm for new episodes.
> ``` console
> cd /etc/cron.d && sudo echo "0 1 * * * root cd /opt/ytdlp2STRM && /usr/bin/python3 /opt/ytdlp2STRM/cli.py --media crunchyroll --params direct" > ytdlp2STRM_crunchyroll_direct
> ```

## SX3 - Anime en Català (Catalan Anime)

* Example cron.d file to create strm files in **direct mode** from channel_list every 24 hours (duration info, no download/disk usage, fast first loading, no cpu usage, redirect to direct twitch url with video/audio merged, faster mode)

> ``` console
> cd /etc/cron.d && sudo echo "0 1 * * * root cd /opt/ytdlp2STRM && /usr/bin/python3 /opt/ytdlp2STRM/cli.py --media sx3 --params direct" > ytdlp2STRM_sx3_direct
> ```


## main.py 
A little script to serve yt-dlp video/audio as HTTP data throught Flask and dynamic URLs. We can use this dynamic URLs with youtube id video in url like http://127.0.0.1:5000/youtube/direct/FxCqhXVc9iY and open it with VLC or save it in .strm file (works in Jellyfin)

## cli.py and 
Controller that loads plugins functions, used to set cronjobs to manage strm files

## config/config.json
* ytdlp2strm_host 
* ytdlp2strm_port
* ytdlp2strm_keep_old_strm

## plugins/*media*/config.json
* strm_output_folder
* channels_list_file
* days_dateafter
* videos_limit
* [YOUTUBE] sponsorblock
* [YOUTUBE] sponsorblock_cats
* [YOUTUBE] [CRUNCHYROLL] proxy
* [YOUTUBE] [CRUNCHYROLL] proxy_url
* [CRUNCHYROLL] crunchyroll_cookies_file
* [CRUNCHYROLL] crunchyroll_audio_language
* [CRUNCHYROLL] crunchyroll_subtitle_language <- embedded in video

## plugins/*media*/channel_list.json
* [YOUTUBE] With "keyword-" prefix you can search for a keyword and this script will create the folders of channels founds dinamically and put inside them the strm files for each video. See an exaple in channel_list.example.json
* [YOUTUBE] Playlist needs "list-" prefix before playlist id, you can see an exaple in channel_list.example.json
* [YOUTUBE] If you want to get livestream from /streams youtube channel tab you need to add a new channel in channel_list with /streams (Check an example in ./plugins/youtube/channel_list.example.json)
* [TWITCH] This script makes a NFO file (tvshow.nfo) for each youtube or twitch channel (to get name, description and images). *Description only works in Linux systems at the moment
* [CRUNCHYROLL] Only support path from URL series (not episodes), the script will create a folder for each seria, and subfolders for each season, inside season folder the strm episodes files  will be created 

## Service
ytdlp2strm.service example service to run main.py with systemctl. 

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
