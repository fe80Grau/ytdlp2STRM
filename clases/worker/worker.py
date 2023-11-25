import os
import subprocess
import shlex

class worker:
    def __init__(self, command):
        self.command = command
        self.wd =  os.path.abspath('.')

    def output(self):
        return subprocess.getoutput(
            ' '.join(
                self.command
            )
        )

    def pipe(self):
        return subprocess.Popen(
            self.command, 
            stdout=subprocess.PIPE,
            universal_newlines=True,
            #encoding='latin-1',
            cwd=self.wd
            #bufsize=1,
            #shell=True
        )

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
                print(output.strip())
        rc = process.poll()
        return rc
