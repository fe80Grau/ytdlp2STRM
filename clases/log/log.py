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

        # Limpiar el archivo de registros antiguos
        self.cleanup_log_once_a_day()

    def write(self):
        with open('ytdlp2strm.log', 'a', encoding="utf-8") as file:
            if self.message != "" and self.message:
                file.write(self.message + '\n')

    def cleanup_log(self):
        log_file = 'ytdlp2strm.log'
        if os.path.exists(log_file):
            with open(log_file, 'r+', encoding='utf-8', errors='ignore') as file:
                lines = file.readlines()
                file.seek(0)
                file.truncate()

                # Calcular el límite de tiempo (7 días atrás)
                now = datetime.datetime.now()
                cutoff = now - datetime.timedelta(days=7)

                for line in lines:
                    try:
                        # Extraer la fecha del registro
                        timestamp_str = line.split(']')[0][1:]
                        log_time = datetime.datetime.fromisoformat(timestamp_str)

                        # Escribir las líneas que están dentro del límite de tiempo
                        if log_time > cutoff:
                            file.write(line)
                    except ValueError:
                        # Si la línea no tiene un formato de fecha válido, se salta
                        continue

    def cleanup_log_once_a_day(self):
        last_cleanup_file = 'log_cleanup.txt'
        now = datetime.datetime.now().date()

        # Verificar la fecha de la última limpieza
        if os.path.exists(last_cleanup_file):
            with open(last_cleanup_file, 'r', encoding='utf-8', errors='ignore') as file:
                last_cleanup_date_str = file.read().strip()
                try:
                    last_cleanup_date = datetime.datetime.fromisoformat(last_cleanup_date_str).date()
                except ValueError:
                    last_cleanup_date = None
        else:
            last_cleanup_date = None

        # Si no se ha limpiado hoy, realizar la limpieza y actualizar la fecha de la última limpieza
        if last_cleanup_date is None or (now - last_cleanup_date).days >= 1:
            self.cleanup_log()
            with open(last_cleanup_file, 'w', encoding='utf-8') as file:
                file.write(now.isoformat())