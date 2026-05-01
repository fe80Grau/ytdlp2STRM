import schedule
import time
from cli import main as main_cli
from clases.config import config as c
from clases.log import log as l
import threading
import re
from tzlocal import get_localzone  # $ pip install tzlocal
import pytz
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import os
import hashlib

# -- LOAD CONFIG AND CHANNELS FILES
config_path = os.path.abspath('./config/crons.json')
running_tasks = {}
running_tasks_lock = threading.Lock()

def calculate_hash(file_path):
    """Calcula el hash SHA-256 del archivo especificado."""
    sha256 = hashlib.sha256()
    try:
        with open(file_path, 'rb') as f:
            while chunk := f.read(8192):
                sha256.update(chunk)
        return sha256.hexdigest()
    except FileNotFoundError:
        return None

def load_crons():
    return c.config(config_path).get_config()
    
class Cron(threading.Thread):
    def __init__(self, stop_event):
        super().__init__(daemon=True)
        self.stop_event = stop_event
        self.observer = Observer()  # Mueve el observador aquí para detenerlo más tarde
        self.config_hash = None
        self.schedule_lock = threading.RLock()
        self.running_tasks = running_tasks
        self.running_tasks_lock = running_tasks_lock

    def run(self):
        try:
            self.default_tz = get_localzone()
            self.schedule_tasks()
            self.watch_config()
        except Exception as e:
            l.log('cron', f"Cron thread stopped unexpectedly: {e}")

    def schedule_tasks(self):
        with self.schedule_lock:
            new_hash = calculate_hash(config_path)
            if self.config_hash == new_hash:
                return
            
            try:
                crons = load_crons()
            except Exception as e:
                l.log('cron', f"Could not load crons configuration: {e}")
                return
            
            if not isinstance(crons, list):
                l.log('cron', "Invalid crons configuration format. Keeping current scheduled tasks.")
                return
            
            self.config_hash = new_hash
            self.crons = crons
            l.log('cron', "Scheduling tasks according to the latest crons configuration.")

            # Cancel any existing scheduled jobs
            for job in schedule.get_jobs():
                schedule.cancel_job(job)

            # Schedule all new tasks
            for cron in self.crons:
                try:
                    if 'timezone' in cron and cron['timezone']:
                        try:
                            local_tz = pytz.timezone(cron['timezone'])
                        except pytz.UnknownTimeZoneError:
                            l.log('cron', f"Unknown timezone {cron['timezone']}, using default {self.default_tz}")
                            local_tz = self.default_tz
                    else:
                        local_tz = self.default_tz

                    local_tz_str = local_tz.zone if isinstance(local_tz, pytz.BaseTzInfo) else str(local_tz)

                    try:
                        qty = int(cron['qty']) if cron['qty'] else 1
                    except ValueError:
                        qty = 1
                        l.log('cron', f"Invalid qty for cron: {cron}, using default value 1.")

                    every_method = getattr(schedule.every(qty), cron['every'])

                    # Wrap main_cli in a thread to prevent blocking
                    task_to_do = lambda params=cron['do']: self.start_task(main_cli, params)

                    if cron['at']:
                        if re.match(r'^\d{2}:\d{2}$', cron['at']):
                            every_method.at(cron['at'], local_tz_str).do(task_to_do)
                            l.log('cron', f"Scheduled task {cron['do']} at {cron['at']} {local_tz_str}.")
                        else:
                            l.log('cron', f"Invalid time format {cron['at']} for cron: {cron}.")
                    else:
                        every_method.do(task_to_do)
                        l.log('cron', f"Scheduled task {cron['do']} every {qty} {cron['every']}.")
                except Exception as e:
                    l.log('cron', f"Could not schedule cron {cron}: {e}")

    def start_task(self, task_func, params):
        task_params = list(params)
        task_key = tuple(task_params)
        with self.running_tasks_lock:
            running_thread = self.running_tasks.get(task_key)
            if running_thread and running_thread.is_alive():
                l.log('cron', f"Skipping task {task_params}: previous execution is still running.")
                return
            thread = threading.Thread(target=self.run_task, args=(task_func, task_params, task_key), daemon=True)
            self.running_tasks[task_key] = thread
            thread.start()

    def run_task(self, task_func, params, task_key):
        started_at = time.monotonic()
        l.log('cron', f"Starting task {params}.")
        try:
            task_func(params)
        except Exception as e:
            l.log('cron', f"Error executing task {params}: {e}")
        finally:
            duration = int(time.monotonic() - started_at)
            l.log('cron', f"Finished task {params} in {duration} seconds.")
            with self.running_tasks_lock:
                if self.running_tasks.get(task_key) is threading.current_thread():
                    del self.running_tasks[task_key]

    def watch_config(self):
        event_handler = ConfigChangeHandler(config_path, callback=self.schedule_tasks)
        self.observer.schedule(event_handler, path=os.path.dirname(config_path), recursive=False)
        self.observer.start()

        l.log('cron', f"Started watching {config_path} for changes.")

        try:
            while not self.stop_event.is_set():
                try:
                    with self.schedule_lock:
                        schedule.run_pending()
                except Exception as e:
                    l.log('cron', f"Error running pending cron tasks: {e}")
                    self.stop_event.wait(5)
                self.stop_event.wait(1)
        except KeyboardInterrupt:
            self.observer.stop()
        finally:
            self.observer.stop()
            self.observer.join()

class ConfigChangeHandler(FileSystemEventHandler):
    def __init__(self, file_path, callback):
        self.file_path = file_path
        self.callback = callback
        self.last_hash = calculate_hash(file_path)

    def on_modified(self, event):
        if event.event_type == 'modified' and os.path.abspath(event.src_path) == os.path.abspath(self.file_path):
            new_hash = calculate_hash(self.file_path)
            if new_hash != self.last_hash:
                self.last_hash = new_hash
                try:
                    self.callback()
                except Exception as e:
                    l.log('cron', f"Error reloading cron configuration: {e}")
