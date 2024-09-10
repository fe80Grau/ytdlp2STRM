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

# -- LOAD CONFIG AND CHANNELS FILES
config_path = os.path.abspath('./config/crons.json')

def load_crons():
    return c.config(config_path).get_config()

class Cron(threading.Thread):
    def __init__(self, stop_event):
        super().__init__(daemon=True)
        self.stop_event = stop_event
        self.observer = Observer()  # Mueve el observador aquí para detenerlo más tarde

    def run(self):
        self.default_tz = get_localzone()        
        self.schedule_tasks()
        self.watch_config()

    def schedule_tasks(self):
        self.crons = load_crons()
        l.log('cron', "Scheduling tasks according to the latest crons configuration.")

        # Cancel any existing scheduled jobs
        for job in schedule.get_jobs():
            schedule.cancel_job(job)
        #l.log('cron', "Cancelled all existing scheduled jobs.")

        # Schedule all new tasks
        for cron in self.crons:
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

            if cron['at']:
                if re.match(r'^\d{2}:\d{2}$', cron['at']):
                    every_method.at(cron['at'], local_tz_str).do(main_cli, cron['do'])
                    l.log('cron', f"Scheduled task {cron['do']} at {cron['at']} {local_tz_str}.")
                else:
                    l.log('cron', f"Invalid time format {cron['at']} for cron: {cron}.")
            else:
                every_method.do(main_cli, cron['do'])
                l.log('cron', f"Scheduled task {cron['do']} every {qty} {cron['every']}.")

    def watch_config(self):
        event_handler = ConfigChangeHandler(callback=self.schedule_tasks)
        self.observer.schedule(event_handler, path=os.path.dirname(config_path), recursive=False)
        self.observer.start()

        l.log('cron', f"Started watching {config_path} for changes.")

        try:
            while not self.stop_event.is_set():
                schedule.run_pending()
                self.stop_event.wait(60)
        except KeyboardInterrupt:
            self.observer.stop()
        self.observer.stop()
        self.observer.join()

class ConfigChangeHandler(FileSystemEventHandler):
    def __init__(self, callback):
        self.callback = callback

    def on_modified(self, event):
        #l.log('cron', f"Detected file modification in {event.src_path}.")
        if event.src_path == config_path:
            l.log('cron', f'{config_path} has been modified')
            self.callback()
