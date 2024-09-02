import os
import datetime
from flask_socketio import emit

class log:
    def __init__(self, author, text):
        now = datetime.datetime.now()
        message = f'[{now}] {author} : {text.strip()}'
        if author == 'ui':
            message = f'{text.strip()}'
        if message.strip() != "" and message:  
            print(message)
        try:
            emit('command_output', f'{message}')
            
        except Exception as e:
            pass
            
        with open('ytdlp2strm.log', 'a') as file:
            if message.strip != "" and message:
                file.write(message + '\n')