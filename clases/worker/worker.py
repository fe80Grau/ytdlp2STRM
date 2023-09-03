import subprocess

class worker:
    def __init__(self, command):
        self.command = command

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
            universal_newlines=True
        )

    def call(self):
        return subprocess.call(
            self.command
        )
