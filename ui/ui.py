import json
import shlex
from clases.config import config as c
from clases.cron import cron as cron
from clases.log import log as l
from flask_socketio import emit
from subprocess import Popen, PIPE

class Ui:
    def __init__(self):
        self.config_file = 'config/config.json'
        self.plugins_file = 'config/plugins.py'
        self.crons_file = 'config/crons.json'

    @property
    def general_settings(self):
        # Leer el archivo de configuración
        data = []
        with open(self.config_file, 'r') as file:
            data = json.load(file)
        return data
    
    @general_settings.setter
    def general_settings(self, data):
        # Guardar los valores en el archivo de configuración
        with open(self.config_file, 'w') as file:
            json.dump(data, file)

    @property
    def plugins_py(self):
        data = []
        with open(self.plugins_file, 'r') as file:
            data = file.read()
        return data
    
    @plugins_py.setter
    def plugins_py(self, data):
        with open(self.plugins_file, 'w', newline="") as file:
            file.write(data)

    @property
    def plugins(self):
        plugins = []
        
        for plugin in self.plugins_py.split('\n'):
            if 'plugins.' in plugin:
                if not '#' in plugin:
                    name = plugin.split('plugins.')[1].split(' ')[0]
                    path = '{}/{}'.format(
                        './plugins',
                        name
                    )
                    config = c.config(
                        '{}/{}'.format(
                            path,
                            'config.json'
                        )
                    ).get_config()

                    channels = c.config(
                        config['channels_list_file']
                    ).get_channels()

                    plugins.append(
                        {
                            'name' : name,
                            'path' : path,
                            'enabled' : True if not '#' in plugin else False,
                            'config' :  config,
                            'channels' : channels
                        }
                    )

        return plugins
    
    @plugins.setter
    def plugins(self, data):
        config_file = data['config_file']
        data.pop('config_file', None)

        if 'channels' in data:
            with open(config_file, 'w', newline="") as file:
                file.write(
                    json.dumps(
                        data['channels'],
                        indent=4
                    )
                )
        else:
            with open(config_file, 'w') as file:
                json.dump(data, file)


    @property
    def crons(self):
        data = []
        with open(self.crons_file, 'r') as file:
            data = json.load(file)
        return data
    
    @crons.setter
    def crons(self, data):
        with open(self.crons_file, 'w', newline="") as file:
            file.write(data)

    def handle_output(self, output):
        emit('command_output', output.strip())  # Enviar a cliente

    def handle_command(self, command):
        # Asegurarse de que el comando se ejecuta sin buffering
        if not '-u' in command:
            if 'python3' in command:
                command = command.replace('python3', 'python3 -u')
            else:
                command = command.replace('python', 'python -u')
        
        secure_command = command.split(' ')
        try :
            if secure_command[2] == 'cli.py':
                
                # Iniciar el proceso
                process = Popen(shlex.split(command), stdout=PIPE, stderr=PIPE, text=True, encoding='utf-8')

                # Leer y emitir la salida en tiempo real
                while True:
                    output = process.stdout.readline()
                    if output == '' and process.poll() is not None:
                        break
                    if output:
                        #print(output.strip())  # Debugging: Imprimir en el servidor
                        #self.handle_output(output)
                        l.log('ui', output)

                
                emit('command_completed', {'data': 'Comando completado'})

                # Manejar salida de error si existe
                _, stderr = process.communicate()
                #if stderr:
                #    emit('command_error', stderr.strip())

                # Importante: Emitir 'command_completed' al finalizar el comando
                #emit('command_completed', {'data': 'Comando completado'})
            else:
                emit('command_output', 'only python cli.py command can be executed from here.')
                emit('command_completed', {'data': 'Comando completado'})
        except:
            emit('command_output', 'only python cli.py command can be executed from here.')
            emit('command_completed', {'data': 'Comando completado'})