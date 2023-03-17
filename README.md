# ytdlp2STRM
* Youtube to STRM files
* Youtube integration with Jellyfin/Emby

## Requierments
* Python 3
* yt-dlp
* Flask

## main.py 
A little script to serve yt-dlp video/audio as HTTP data throught Flask and dynamic URLs. We can use this dynamic URLs with youtube id video in url like http://127.0.0.1:5000/youtube/stream/FxCqhXVc9iY and open it with VLC or save it in .strm file (works in Jellyfin)

## cli.py and channel_list.py
A little script to list last 60 days videos in channels setted on channel_list.py and save all as .strm files . I added id channels and videos in names [xxxx] for YoutubeMetadata Jellyfin plugin integration.

## Service
ytdlp2strm.service example service to run main.py with systemctl . Put it into /etc/systemd/system and run systemctl enable ytdlp2strm.service , systemctl start ytdlp2strm.service

## Examples
* Example commands to generate strm files
> * Download file (cached mode, duration info, disk usage)
> ```console
> cli.py --m make_files_strm --p youtube,download
> ```

* Stream content (no duration info, no disk usage)
> ```console
> cli.py --m make_files_strm --p youtube,stream
> ```

* Edit variable media_folder , host and port /by default http://127.0.0.1 and 5000

* Example cron.d file to create to create strm files from channel_list every 2 horus
> ``` console
> cd /etc/cron.d && sudo echo "00 22 * * * root /usr/bin/python3 /opt/ytdlp2STRM/cli.py --m make_files_strm --p youtube,download" > ytdlp2STRM
> ```

## Credits
[![GitHub - ShieldsIO](https://img.shields.io/badge/GitHub-ShieldsIO-42b983?logo=GitHub)](https://github.com/badges/shields)
[![GitHub - Flask](https://img.shields.io/badge/GitHub-Flask-0000ff?logo=GitHub)](https://github.com/pallets/flask)
[![GitHub - yt-dlp](https://img.shields.io/badge/GitHub-ytdlp-ff0000?logo=GitHub)](https://github.com/yt-dlp/yt-dlp)
[![GitHub - andreztz](https://img.shields.io/badge/GitHub-andreztz-ffc230?logo=GitHub)](https://gist.github.com/andreztz/9e472fa6daa17d2f954958fc33e5a296)