import os
import datetime
from flask_socketio import emit
import sys
import io


# Cambiar el codec por defecto a UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)

class log:
    def __init__(self, author, text):
        now = datetime.datetime.now()
        text = text.strip()
        self.message = f'[{now}] {author} : {text}'

        if author == 'ui':
            self.message = f'{text}'
        if self.message != "" and self.message:
            print(self.message)
            sys.stdout.flush()  # Forzar el vaciado del buffer
            try:
                emit('command_output', f'{self.message}')
            except Exception as e:
                self.write()

    def write(self):
        with open('ytdlp2strm.log', 'a', encoding="utf-8") as file:
            if self.message != "" and self.message:
                file.write(self.message + '\n')

# Ejemplo de uso
if __name__ == "__main__":
    log_instance = log("author_example", "Este es un mensaje con un emoji 🚀")
