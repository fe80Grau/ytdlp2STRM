import os
import glob
import shutil
import time

class folders:
    keep_downloaded = 1800

    def make_clean_folder(self, folder_path, forceclean, config):
        # Verificar si el directorio existe
        if os.path.exists(folder_path):
            # Verificar si se debe realizar una limpieza forzada
            if forceclean or not config.get("ytdlp2strm_keep_old_strm", True):
                # Obtener la lista de archivos en el directorio
                file_list = glob.glob(os.path.join(folder_path, "*"))

                # Eliminar los archivos en el directorio
                for file_path in file_list:
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                        print(f"Deleted file: {file_path}")

                print(f"Cleaned direcotry: {folder_path}")
        else:
            # Crear el directorio y subdirectorios
            os.makedirs(folder_path, exist_ok=True)

            print(f"Created directory: {folder_path}")

    def write_file(self, file_path, content):
        # Escribir el contenido en el archivo
        try:
            with open(file_path, "w") as file:
                file.write(content.replace('\n',''))

            print(f"File created: {file_path}")
        except:
            pass

    def clean_old_videos(self):
        while True:
            try:
                time.sleep(60)
                path = os.getcwd()
                now = time.time()
                for f in os.listdir(path):
                    extension = f.split('.')[-1]
                    if extension == "webm" and os.stat(f).st_ctime < now - self.keep_downloaded:
                        if os.path.isfile(f):
                            os.remove(os.path.join(path, f))
            except:
                continue
        pass