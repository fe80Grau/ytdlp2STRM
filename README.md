# ytdlp2STRM
* Youtube to STRM files
* Youtube integration with Jellyfin/Emby (Requires YoutubeMetadata plugin)
![image](https://user-images.githubusercontent.com/6680464/227725095-8451ea3b-d404-47d7-82b6-59ec9f683eb2.png)

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
* Create folder to store .strm files (by default /media/Youtube)
```console
mkdir /media/Youtube
```
* EDIT channel_list.example.json with your channels names (you can see channel name (or ID or USER)  after first / (slash) in youtube channel URL). Save it as channel_list.json (delete .example sufix).
* Edit config.json [and ytdlp2strm.service with your preferences and copy ytdlp2strm.service to /etc/systemd/system]*Between brackets only Linux.
* I'm testing SponsorBlock. Requieres ffmpeg custom build from yt-dlp. https://github.com/yt-dlp/FFmpeg-Builds#ffmpeg-static-auto-builds (Download your version Linux x64 or LinuxARM64, Windows x64 or Windows x86), extract an replace binaries in bin folder in your system. Normaly ffmpeg, ffprobe and ffplay binaries are installed in /usr/bin/ , back up orginials before replace. 
* SponsorBlock is disabled by default in config.json
* SponsorBlock categories: sponsor, intro, outro, selfpromo, preview, filler, interaction, music_offtopic, poi_highlight, chapter, all. By default is setted sponsor.
```console
sudo cp ytdlp2strm.service /etc/systemd/system/ytdlp2strm.service
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

* Example cron.d file to create strm files in **redirect mode** from channel_list every 2 hours (duration info, no download/disk usage, fast first loading, no cpu usage, redirect to direct youtube url with video/audio merged)
* SponsorBlock not works on redirect mode
> ``` console
> cd /etc/cron.d && sudo echo "0 */2 * * * root cd /opt/ytdlp2STRM && /usr/bin/python3 /opt/ytdlp2STRM/cli.py --m make_files_strm --p youtube,redirect" > ytdlp2STRM
> ```
* Example cron.d file to create strm files in **download mode** from channel_list every 2 hours (cached mode, duration info, temp disk usage, slow first loading)
> ``` console
> cd /etc/cron.d && sudo echo "0 */2 * * * root cd /opt/ytdlp2STRM && /usr/bin/python3 /opt/ytdlp2STRM/cli.py --m make_files_strm --p youtube,download" > ytdlp2STRM
> ```
* Example cron.d file to create strm files in **stream mode** from channel_list every 2 hours (no duration info, no download/disk usage, fast first loading)
> ``` console
> cd /etc/cron.d && sudo echo "0 */2 * * * root cd /opt/ytdlp2STRM && /usr/bin/python3 /opt/ytdlp2STRM/cli.py --m make_files_strm --p youtube,stream" > ytdlp2STRM
> ```

* After that you can see all channels folders under /media/Youtube and strm files inside them. If you are using Jellyfin/Emby, add /media/Youtube as folder in Library and enjoy it!

## main.py 
A little script to serve yt-dlp video/audio as HTTP data throught Flask and dynamic URLs. We can use this dynamic URLs with youtube id video in url like http://127.0.0.1:5000/youtube/redirect/FxCqhXVc9iY and open it with VLC or save it in .strm file (works in Jellyfin)

## cli.py and channel_list.json
A little script to list N videos (by default 10) from N days (by default 10) ago to today in channels declared in channel_list.json and save all as .strm files (you can change them in config.json) . Added id channels and videos in names [xxxx] for YoutubeMetadata Jellyfin plugin integration.

* Playlist needs "list-" prefix before playlist id, you can see an exaple in channel_list.example.json
* NFO (tvshow.nfo) for each youtube channel (to get name, description and images). *Description only works in Linux systems at the moment

## Service
ytdlp2strm.service example service to run main.py with systemctl. 

## Pendings
* Include subtitles
* Video quality. Config options: Forced (worst, balanced, best) or Dynamic (depends connection speed)
* Get Youtube account subscrition channel list
* Crunchyroll integration
* Do this as a Jellyfin plugin with GUI (settings and search for channels to add in list)

## Credits
[![GitHub - ShieldsIO](https://img.shields.io/badge/GitHub-ShieldsIO-42b983?logo=GitHub)](https://github.com/badges/shields)
[![GitHub - Flask](https://img.shields.io/badge/GitHub-Flask-0000ff?logo=GitHub)](https://github.com/pallets/flask)
[![GitHub - yt-dlp](https://img.shields.io/badge/GitHub-ytdlp-ff0000?logo=GitHub)](https://github.com/yt-dlp/yt-dlp)
[![GitHub - andreztz](https://img.shields.io/badge/GitHub-andreztz-ffc230?logo=GitHub)](https://gist.github.com/andreztz/9e472fa6daa17d2f954958fc33e5a296)
