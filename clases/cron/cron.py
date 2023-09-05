import schedule
import time
from cli import main as main_cli
from clases.config import config as c
import threading

## -- LOAD CONFIG AND CHANNELS FILES
crons = c.config(
    './config/crons.json'
).get_config()

class Cron(threading.Thread):
    def __init__(self):
        super().__init__(
            daemon=True
        )

    def run(self):
        for cron in crons:     
            call_constructor = "schedule.every({}).{}.at('{}').do(main_cli, {})".format(
                cron['qty'],
                cron['every'],
                cron['at'],
                cron['do']
            ).replace(
                '.at()',
                ''
            )
            #schedule.every().day.at('10:30').do(main_cli, ['--media', 'sx3', '--params', 'direct'])
            print("Reading crons:")
            print(call_constructor)
            r = eval(
                call_constructor
            )

        while True:
            try:
                schedule.run_pending()
                time.sleep(60)
            except:
                continue
        pass
