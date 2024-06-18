import os
import glob
import time
import platform
from clases.config import config as c
import threading

class folders:
    ytdlp2strm_config = c.config('./config/config.json').get_config()

    keep_downloaded = 86400
    temp_aria2_ffmpeg_files = 600
    if 'ytdlp2strm_temp_file_duration' in ytdlp2strm_config:
        keep_downloaded = int(ytdlp2strm_config['ytdlp2strm_temp_file_duration'])

    def make_clean_folder(self, folder_path, forceclean, config):
        if os.path.exists(folder_path):
            if forceclean or not config.get("ytdlp2strm_keep_old_strm", True):
                file_list = glob.glob(os.path.join(folder_path, "*"))
                for file_path in file_list:
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                        print(f"Deleted file: {file_path}")
                print(f"Cleaned directory: {folder_path}")
        else:
            os.makedirs(folder_path, exist_ok=True)
            print(f"Created directory: {folder_path}")

    def write_file(self, file_path, content):
        try:
            with open(file_path, "w") as file:
                file.write(content.replace('\n',''))
            print(f"File created: {file_path}")
        except Exception as e:
            print(f"Error writing file: {e}")
            pass
        
    def clean_waste(self, files_to_delete):
        for file_path in files_to_delete:
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)
                else:
                    continue
            except Exception as e:
                print(f"Error deleting file {file_path}: {e}")
                pass

    def clean_old_videos(self, stop_event):
        def creation_date(path_to_file):
            if platform.system() == 'Windows':
                return os.path.getctime(path_to_file)
            else:
                stat = os.stat(path_to_file)
                try:
                    return stat.st_birthtime
                except AttributeError:
                    return stat.st_mtime

        def modified_date(path_to_file):
            stat = os.stat(path_to_file)
            return stat.st_mtime
        
        while not stop_event.is_set():
            try:
                time.sleep(5)
                path = os.getcwd()
                temp_path = os.path.join(path, 'temp')
                now = time.time()
                aria2_ffmpeg_files = ['.part', 'aria2', 'urls', '.temp', 'm4a', '.ytdl']

                for f in os.listdir(temp_path):
                    temp_file = os.path.join(temp_path, f)
                    if not f == "__init__.py":
                        if any(keyword in f for keyword in aria2_ffmpeg_files):
                            if os.path.isfile(temp_file) and modified_date(temp_file) < now - self.temp_aria2_ffmpeg_files:
                                print(f"Removing old temporary file: {temp_file}")
                                os.remove(temp_file)
                        else:
                            if os.path.isfile(temp_file) and modified_date(temp_file) < now - self.keep_downloaded:
                                print(f"Removing old video file: {temp_file}")
                                os.remove(temp_file)
            except Exception as e:
                print(f"Error in clean_old_videos: {e}")
                continue
        print("Exiting clean_old_videos thread.")
