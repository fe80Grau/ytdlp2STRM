import os
import datetime
from flask_socketio import emit

class log:
    def __init__(self, author, text):
        now = datetime.datetime.now()
        text = text.strip()
        message = f'[{now}] {author} : {text}'
        if author == 'ui':
            message = f'{text}'
        if message.strip() != "" and message:  
            print(message)
        try:
            emit('command_output', f'{message}')
            
        except Exception as e:
            pass
            
        with open('ytdlp2strm.log', 'a', encoding="utf-8") as file:
            if message.strip != "" and message:
                file.write(message + '\n')