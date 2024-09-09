import os
import subprocess
import shlex
import requests
import time
import threading
from clases.log import log as l

# Inicializa un objeto Lock para el control de concurrencia
preload_lock = threading.Lock()

# Variable de cierre para controlar la ejecución concurrente de la función preload_video
is_preloading = False


class worker:
    def __init__(self, command):
        self.command = command
        self.wd =  os.path.abspath('.')

    def output(self):
        process = subprocess.run(
            self.command,  # Unimos el comando en una cadena de texto
            #shell=True,
            capture_output=True,  # Capturamos stdout y stderr
            text=True
        )
        if process.stderr:
            if not 'The channel is not currently live' in process.stderr and not '[twitch:stream] videos: videos does not exist' in process.stderr:
                l.log("worker", process.stderr)
        return process.stdout
    
    def shell(self):
        process = subprocess.run(
            ' '.join(self.command),  # Unimos el comando en una cadena de texto
            shell=True,
            capture_output=True  # Capturamos stdout y stderr
        )
        try:
            return process.stdout.decode('utf-8')  # Intentamos decodificar como UTF-8
        except UnicodeDecodeError:
            return process.stdout.decode('latin1')  # Intentamos decodificar con latin1

    
    def call(self):
        return subprocess.call(
            self.command
        )


    def run(self):
        process = subprocess.Popen(self.command, stdout=subprocess.PIPE, shell=True)
        while True:
            line = process.stdout.readline().rstrip()
            if not line:
                break
            try:
                yield line.decode('utf-8')
            except:
                yield line.decode('latin-1')


    def run_command(self):
        process = subprocess.Popen(shlex.split(self.command), stdout=subprocess.PIPE)
        while True:
            try:
                output = process.stdout.readline().rstrip().decode('utf-8')
            except:
                output = process.stdout.readline().rstrip().decode('latin-1')
            if output == '' and process.poll() is not None:
                break
            if output:
                log_text = (output.strip())
                l.log("worker", log_text)
        rc = process.poll()
        return rc

    def preload(self):
        global is_preloading

        current_dir = os.getcwd()

        # Construyes la ruta hacia la carpeta 'temp' dentro del directorio actual
        temp_dir = os.path.join(current_dir, 'temp')

        # Intenta adquirir el Lock
        if not preload_lock.acquire(blocking=False):
            # Si no se puede adquirir el Lock, significa que otra instancia ya está ejecutando preload_video
            return
        
        # Verifica si ya se está ejecutando la función
        if is_preloading:
            preload_lock.release()  # No olvides liberar el Lock si decides no proceder
            return
        
        is_preloading = True  # Marca el inicio de la ejecución

        def download_and_cancel():
            try:
                with requests.get(self.command, stream=True) as r:
                    time.sleep(5)  # Esperamos 5 segundos y luego cancelamos la solicitud
            except:
                log_text = ("error on preloading {}".format(self.command))
                l.log("worker", log_text)

        video_id = self.command.split('_')[-1]

        isin = False
        # Iterar sobre todos los archivos en la carpeta 'temp'
        for filename in os.listdir(temp_dir):
            # Comprobar si el crunchroll_id está en el nombre del archivo
            if video_id in filename:
                isin = True
                # Si necesitas hacer algo más que imprimir, este es el lugar.
                # Por ejemplo, podrías romper el bucle con 'break' si solo te interesa saber si al menos uno existe

        if not isin:
            preload_thread = threading.Thread(target=download_and_cancel)
            preload_thread.start()

        is_preloading = False  # Restablece el estado
        preload_lock.release()  # Libera el Lock