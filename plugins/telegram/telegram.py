
import os
import re
import socket
import asyncio
import threading
import subprocess
from multiprocessing import Process
from telethon import TelegramClient
from sanitize_filename import sanitize
from clases.config import config as c
from clases.worker import worker as w
from clases.folders import folders as f
from clases.nfo import nfo as n

## -- CRUNCHYROLL CLASS
class Telegram:
    def __init__(self, channel=None, api_id=None, api_hash=None, session_file=None):
        self.channel = channel.split('/')[-1] if channel else None
        self.api_id = api_id
        self.api_hash = api_hash
        self.session_name = session_file.rsplit('.', 1)[0] if session_file else None
        self.client = TelegramClient(self.session_name, self.api_id, self.api_hash)
        self.videos = []
        self.current_series_title = '' # Will be set later in get_group_topic

    def extract_serie(self, message):
        if re.search(r"titulo|título|sinopsis|episodios|episodes|serie", message.text or "", re.IGNORECASE):
            # Intenta dividir el mensaje en título por los dos puntos
            split_text = re.split(r":\s*", message.text, 1)
            if len(split_text) > 1:
                title_line = split_text[1].split("\n")[0]
                # Chequear por caracteres no latinos
                if not re.match(r"^[A-Za-z0-9 \-.,'?!;:@()\[\]áéíóúÁÉÍÓÚñÑüÜ]+$", title_line):
                    # Si contiene caracteres no latinos, el título de la serie será la primera línea del texto del mensaje
                    title_line = message.text.split("\n")[0]
                self.current_series_title = title_line.strip()
        
        if ',' in self.current_series_title:
            self.current_series_title = message.text.split("\n")[0]

    def extract_seasson(self, message_text):
        # Buscar patrones para las temporadas en el texto del mensaje
        patterns = [
            r'S(\d{2})',  # Busca patrones como S01, S02, ...
            r'Season (\d+)',  # Busca patrones como Season 1, Season 2, ...
            r'Temporada (\d+)',  # Busca patrones como Temporada 1, Temporada 2, ...
        ]
        
        for pattern in patterns:
            match = re.search(pattern, message_text, re.IGNORECASE)
            if match:
                return match.group(1).zfill(2)  # Retorna el número de la temporada con formato de 2 dígitos

        # Retorna "00" si no hay coincidencias
        return "00"
    
    def extract_episode(self, message_text):
        # Buscar patrones para los episodios en el texto del mensaje
        patterns = [
            r'E(\d{2})',  # Busca patrones como E01, E02, ...
            r'e (\d{2})',  # Busca patrones como e 01, e 02, ...
            r'Episode (\d+)',  # Busca patrones como Episode 1, Episode 2, ...
            r'Episodio (\d+)',  # Busca patrones como Episodio 1, Episodio 2, ...
            r'Capítulo (\d+)',  # Busca patrones como Episodio 1, Episodio 2, ...
            r'Capitulo (\d+)',  # Busca patrones como Episodio 1, Episodio 2, ...
            r'\b(\d{2})\b$'  # Busca números de dos dígitos al final del texto
        ]
        
        for pattern in patterns:
            match = re.search(pattern, message_text, re.IGNORECASE)
            if match:
                return match.group(1).zfill(2)  # Retorna el número del episodio con formato de 2 dígitos

        # Retorna "00" si no hay coincidencias
        return "00"
    
    def extract_episode_name(self, message_text, series_title):
        # Define palabras a ignorar y el patrón para buscar palabras
        ignore_words = ['episode', 'episodio', 'season', 'temporada']
        pattern = r'\b([A-Za-z]{3,})\b'

        # Encuentra todas las palabras que cumplan con el patrón
        words = re.findall(pattern, message_text, re.IGNORECASE)

        # Filtra las palabras ignoradas y une las restantes para formar el nombre del episodio
        filtered_words = [word for word in words if word.lower() not in [ignore_word.lower() for ignore_word in ignore_words]]
        episode_name = ' '.join(filtered_words)

        # Si no se encontraron palabras válidas, el nombre del episodio será el nombre de la serie
        if not filtered_words:
            return series_title

        return episode_name
    
    async def get_videos(self):
        async with self.client:
            entity = await self.client.get_entity(self.channel)

            async for message in self.client.iter_messages(entity, reverse=True):
                if message.video:
                    # Actualiza el group_topic para cada video
                    if not re.search(r"trailer", message.text, re.IGNORECASE):
                        video_id = message.id
                        message_text = message.text or ""
                        video_info = {
                            "channel" : self.channel,
                            "id": video_id,
                            "series_title": self.current_series_title,
                            "seasson" : self.extract_seasson(message_text),
                            "episode" : self.extract_episode(message_text),
                            "episode_name" : self.extract_episode_name(message_text.split('.')[0].split('\n')[0], self.current_series_title)
                        }
                        self.videos.append(video_info)
                else:
                    self.extract_serie(message)
    
    
    @classmethod
    async def create_and_fetch_videos(cls, channel, api_id, api_hash, session_file):
        instance = cls(channel, api_id, api_hash, session_file)
        await instance.get_videos()
        return instance
## -- END

## -- LOAD CONFIG AND CHANNELS FILES
ytdlp2strm_config = c.config(
    './config/config.json'
).get_config()

config = c.config(
    './plugins/telegram/config.json'
).get_config()

channels = c.config(
    config["channels_list_file"]
).get_channels()

source_platform = "telegram"
media_folder = config["strm_output_folder"]
channels_list = config["channels_list_file"]
api_id = config["telegram_api_id"]
api_hash = config["telegram_api_hash"]
session_file = config["telegram_session_file"]
## -- END

## -- telegram-video-downloader
def is_telegram_video_downloader(puerto):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", puerto))
    except socket.error as e:
        if e.errno == 98:  # Código de error para "dirección ya en uso" en Linux
            return True
    except OSError as e:
        if e.errno == 48:  # Código de error para "dirección ya en uso" en MacOS
            return True
        elif e.errno == 10048:  # Código de error para "dirección ya en uso" en Windows
            return True
    else:
        s.close()
        return False
    s.close()
    return True

def telegram_video_downloader():
    # Este es el comando que deseas ejecutar
    command = f'telegram-video-downloader --api_id {api_id} --api_hash {api_hash} --session_file "{session_file}"'
    # Usamos subprocess para ejecutar el comando
    try:
        process = subprocess.run(command, shell=True)
    finally:
        try:
            process.kill()
        except:
            pass

if not is_telegram_video_downloader(5151):
    thread_telegram_video_downloader = threading.Thread(target=telegram_video_downloader)
    # Configuramos el thread como un demonio para que termine cuando el programa principal termine
    thread_telegram_video_downloader.daemon = True
    # Iniciamos el thread
    thread_telegram_video_downloader.start()

else:
    print("ya está en ejecución")
## -- EMD

## -- MANDATORY TO_STRM FUNCTION 
async def get_data():
    for telegram_channel in channels:
        print("Preparing channel {}".format(telegram_channel))

        telegram = await Telegram.create_and_fetch_videos(
            telegram_channel,
            api_id,
            api_hash,
            session_file
        )
        


        for video in telegram.videos:
            video_id = video['id']
            serie = video['series_title']
            season_number = video['seasson']
            episode_number = video['episode']
            episode = video['episode_name']

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
                'direct', 
                f'{telegram.channel}-{video_id}'
            )
            file_path = "{}/{}/{}/{}.{}".format(
                media_folder,  
                sanitize(
                    "{}".format(
                        serie
                    )
                ),  
                sanitize(
                    "S{}".format(
                        season_number
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
                            serie
                        )
                    ),  
                    sanitize(
                        "S{}".format(
                            season_number
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


    return telegram.videos 


def to_strm(method):
    videos = asyncio.run(
        get_data()
    )

## -- END

def direct(telegram_id):
    pass