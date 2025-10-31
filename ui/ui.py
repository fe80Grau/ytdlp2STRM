import json
import shlex
import os
import datetime
import schedule
from clases.config import config as c
from clases.cron import cron as cron
from clases.log import log as l
from flask_socketio import emit
from subprocess import Popen, PIPE

class Ui:
    cli_history = []  # Historial del CLI compartido entre todas las instancias
    max_history_lines = 1000  # Máximo de líneas a mantener
    is_running = False  # Estado de ejecución compartido

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
                # Determinar si el plugin está habilitado
                is_enabled = not '#' in plugin
                
                # Extraer el nombre del plugin (con o sin #)
                if is_enabled:
                    name = plugin.split('plugins.')[1].split(' ')[0]
                else:
                    # Si está comentado, remover el # para obtener el nombre
                    name = plugin.split('plugins.')[1].split(' ')[0]
                
                path = '{}/{}'.format(
                    './plugins',
                    name
                )
                
                try:
                    config = c.config(
                        '{}/{}'.format(
                            path,
                            'config.json'
                        )
                    ).get_config()

                    channels = c.config(
                        config['channels_list_file']
                    ).get_channels()
                except:
                    # Si no se puede cargar la config, usar valores por defecto
                    config = {}
                    channels = None

                plugins.append(
                    {
                        'name' : name,
                        'path' : path,
                        'enabled' : is_enabled,
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

    def get_last_executions(self):
        """Obtiene la última ejecución de cada plugin desde los logs"""
        log_file = 'ytdlp2strm.log'
        last_executions = {}
        
        if not os.path.exists(log_file):
            return last_executions
        
        try:
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as file:
                lines = file.readlines()
                
                # Leer el archivo de atrás hacia adelante para encontrar la última ejecución
                for line in reversed(lines):
                    try:
                        # Buscar líneas que contengan "Running <plugin> with"
                        if 'CLI : Running' in line and 'with' in line:
                            # Extraer timestamp
                            timestamp_str = line.split(']')[0][1:]
                            log_time = datetime.datetime.fromisoformat(timestamp_str)
                            
                            # Extraer nombre del plugin
                            plugin_name = line.split('Running ')[1].split(' with')[0].strip()
                            
                            # Solo guardar si no tenemos ya una ejecución más reciente
                            if plugin_name not in last_executions:
                                last_executions[plugin_name] = log_time
                    except (ValueError, IndexError):
                        continue
        except Exception as e:
            pass
        
        return last_executions

    def get_next_executions(self):
        """Obtiene la próxima ejecución de cada CRON desde schedule"""
        next_executions = {}
        
        try:
            # Obtener todos los jobs programados
            jobs = schedule.get_jobs()
            
            for job in jobs:
                try:
                    # El job tiene la información del comando en job.job_func.args
                    if hasattr(job.job_func, 'args') and job.job_func.args:
                        command_args = job.job_func.args[0]
                        if isinstance(command_args, list) and len(command_args) > 1:
                            # Extraer el nombre del plugin del comando
                            plugin_name = command_args[1]
                            
                            # Obtener la próxima ejecución
                            next_run = job.next_run
                            
                            # Solo guardar si no tenemos ya una ejecución más cercana
                            if plugin_name not in next_executions or next_run < next_executions[plugin_name]:
                                next_executions[plugin_name] = next_run
                except (AttributeError, IndexError, TypeError):
                    continue
        except Exception as e:
            pass
        
        return next_executions

    def handle_output(self, output):
        output_text = output.strip()
        # Agregar al historial
        Ui.cli_history.append(output_text)
        # Mantener solo las últimas max_history_lines líneas
        if len(Ui.cli_history) > Ui.max_history_lines:
            Ui.cli_history = Ui.cli_history[-Ui.max_history_lines:]
        # Enviar a todos los clientes conectados
        emit('command_output', output_text, broadcast=True)

    def handle_command(self, command):
        # Marcar que hay una ejecución en curso
        Ui.is_running = True
        emit('execution_started', {}, broadcast=True)
        
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
                        self.handle_output(output)
                        l.log('ui', output)

                
                # Marcar que la ejecución terminó
                Ui.is_running = False
                emit('command_completed', {'data': 'Comando completado'}, broadcast=True)

                # Manejar salida de error si existe
                _, stderr = process.communicate()
                #if stderr:
                #    emit('command_error', stderr.strip())

                # Importante: Emitir 'command_completed' al finalizar el comando
                #emit('command_completed', {'data': 'Comando completado'})
            else:
                self.handle_output('only python cli.py command can be executed from here.')
                Ui.is_running = False
                emit('command_completed', {'data': 'Comando completado'}, broadcast=True)
        except:
            self.handle_output('only python cli.py command can be executed from here.')
            Ui.is_running = False
            emit('command_completed', {'data': 'Comando completado'}, broadcast=True)