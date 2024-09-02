import schedule
import time
from cli import main as main_cli
from clases.config import config as c
from clases.log import log as l
import threading
import re 
from tzlocal import get_localzone # $ pip install tzlocal

# -- LOAD CONFIG AND CHANNELS FILES
crons = c.config('./config/crons.json').get_config()

class Cron(threading.Thread):
    def __init__(self, stop_event):
        super().__init__(daemon=True)
        self.stop_event = stop_event

    def run(self):
        local_tz = get_localzone() 

        for cron in crons:
            if 'timezone' in cron:
                if not cron['timezone'] == '':
                    local_tz = cron['timezone']
                else:
                    local_tz = get_localzone()
            else:
                local_tz = get_localzone() 

            call_constructor = "schedule.every({}).{}.at('{}', '{}').do(main_cli, {})".format(
                cron['qty'],
                cron['every'],
                cron['at'],
                local_tz,
                cron['do']
            )

            call_constructor = re.sub(r'\.at\(\'\'\,.*?\)', '', call_constructor)
            call_constructor = re.sub(r"\.at\(''\,.*?\)", '', call_constructor)

            r = eval(call_constructor)

        while not self.stop_event.is_set():
            try:
                schedule.run_pending()
                # Usa una espera con timeout para poder verificar la señal de parada
                self.stop_event.wait(60)
            except Exception as e:
                log_text = (e)
                l.log("cron", log_text)

                pass
