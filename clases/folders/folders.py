import os
import glob
import time
import platform
from clases.config import config as c
from clases.log import log as l
import threading

class folders:
    ytdlp2strm_config = c.config('./config/config.json').get_config()

    keep_downloaded = 86400
    temp_aria2_ffmpeg_files = 600
    if 'ytdlp2strm_temp_file_duration' in ytdlp2strm_config:
        keep_downloaded = int(ytdlp2strm_config['ytdlp2strm_temp_file_duration'])

class folders:
    ytdlp2strm_config = c.config('./config/config.json').get_config()

    keep_downloaded = 86400
    temp_aria2_ffmpeg_files = 600
    if 'ytdlp2strm_temp_file_duration' in ytdlp2strm_config:
        keep_downloaded = int(ytdlp2strm_config['ytdlp2strm_temp_file_duration'])

    def make_clean_folder(self, folder_path, forceclean, config):
        if os.path.exists(folder_path):
            if forceclean or config.get("ytdlp2strm_keep_old_strm") == "False":
                # Check the contents of the directory in a simpler way
                try:
                    file_list = os.listdir(folder_path)
                except Exception as e:
                    return

                now = time.time()

                for file_name in file_list:
                    file_path = os.path.join(folder_path, file_name)
                    if os.path.isfile(file_path):
                        try:
                            os.remove(file_path)
                            log_text = f"Deleted file: {file_path}"
                            l.log("folder", log_text)
                            print(log_text)
                        except Exception as e:
                            log_text = f"Failed to delete file: {file_path}. Error: {e}"
                            l.log("folder", log_text)
                log_text = f"Cleaned directory: {folder_path}"
                l.log("folder", log_text)
        else:
            os.makedirs(folder_path, exist_ok=True)
            log_text = f"Created directory: {folder_path}"
            l.log("folder", log_text)


    def write_file(self, file_path, content):
        try:
            if not os.path.exists(file_path) or 'tvshow.nfo' in file_path:
                # Ensure content is properly encoded
                content = content.encode('utf-8').decode('utf-8')
                
                # Write to file with UTF-8 encoding
                with open(file_path, "w", encoding="utf-8") as file:
                    file.write(content.replace('\n',''))
                
                file_path = file_path.encode('utf-8').decode('utf-8')
                log_text = f"File created: {file_path}"
                l.log("folder", log_text)
        except Exception as e:
            log_text = f"Error writing file: {e}"
            l.log("folder", log_text)

    def write_file_spaces(self, file_path, content):
        try:
            if not os.path.exists(file_path) or 'tvshow.nfo' in file_path:
                # Ensure content is properly encoded
                content = content.encode('utf-8').decode('utf-8')
                
                # Write to file with UTF-8 encoding
                with open(file_path, "w", encoding="utf-8") as file:
                    file.write(content)
                
                file_path = file_path.encode('utf-8').decode('utf-8')
                log_text = f"File created: {file_path}"
                l.log("folder", log_text)
        except Exception as e:
            log_text = f"Error writing file: {e}"
            l.log("folder", log_text)

    def clean_waste(self, files_to_delete):
        for file_path in files_to_delete:
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)
                else:
                    continue
            except Exception as e:
                log_text = (f"Error deleting file {file_path}: {e}")
                l.log("folder", log_text)
                pass

    def creation_date(self, path_to_file):
        if platform.system() == 'Windows':
            return os.path.getctime(path_to_file)
        else:
            stat = os.stat(path_to_file)
            try:
                return stat.st_birthtime
            except AttributeError:
                return stat.st_mtime

    def modified_date(self, path_to_file):
        stat = os.stat(path_to_file)
        return stat.st_mtime
    
    def clean_old_videos(self, stop_event):

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
                            if os.path.isfile(temp_file) and self.modified_date(temp_file) < now - self.temp_aria2_ffmpeg_files:
                                log_text = (f"Removing old temporary file: {temp_file}")
                                l.log("folder", log_text)
                                os.remove(temp_file)
                        else:
                            if os.path.isfile(temp_file) and self.modified_date(temp_file) < now - self.keep_downloaded:
                                log_text = (f"Removing old video file: {temp_file}")
                                l.log("folder", log_text)
                                os.remove(temp_file)
            except Exception as e:
                log_text = (f"Error in clean_old_videos: {e}")
                l.log("folder", log_text)
                continue
        log_text = ("Exiting clean_old_videos thread.")
        l.log("folder", log_text)
