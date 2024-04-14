from __main__ import app
from flask_socketio import SocketIO, emit
from flask import request, render_template
from subprocess import Popen, PIPE
import shlex
import json
from clases.worker import worker as w
from ui.ui import Ui
_ui = Ui()
socketio = SocketIO(app)

# Ruta principal
@app.route('/')
def index():
    crons = _ui.crons
    return render_template(
        'index.html',
        plugins=_ui.plugins,
        crons=crons
    )

# Ruta para las opciones generales
@app.route('/general', methods=['GET', 'POST'])
def general_settings():
    
    result = False
    if request.method == 'POST':
        # Obtener los valores del formulario
        config_data = {}
        for key, value in request.form.items():
            config_data[key] = value

        _ui.general_settings = config_data

    config_data = _ui.general_settings
    if config_data:
        result = True

    return render_template(
        'general_settings.html', 
        config_data=config_data, 
        result=result, 
        request=request.method
    )

# Ruta para la edición de plugins
@app.route('/plugins', methods=['GET', 'POST'])
def plugin_py_settings():
    result = False
    if request.method == 'POST':
        # Obtener el código de plugins desde el formulario
        plugin_code = request.form.getlist('plugin_field')
        # Guardar el código en el archivo de plugins
        _ui.plugins_py = '\n'.join(plugin_code)
        

    plugin_code = _ui.plugins_py.splitlines()

    if plugin_code:
        result = True

    return render_template(
        'plugin_py_settings.html', 
        result=result,
        plugin_code=plugin_code, 
        request=request.method
    )

# Ruta para la edición de plugins
@app.route('/crons', methods=['GET', 'POST'])
def crons_settings():
    result = False
    if request.method == 'POST':
        # Obtener el código de plugins desde el formulario
        headers = ('every', 'qty', 'at', 'timezone', 'plugin', 'param')
        values = (
            request.form.getlist('every[]'),
            request.form.getlist('qty[]'),
            request.form.getlist('at[]'),
            request.form.getlist('timezone[]'),
            request.form.getlist('plugin[]'),
            request.form.getlist('param[]'),
        )
        crons = [{} for i in range(len(values[0]))]
        for x,i in enumerate(values):
            for _x,_i in enumerate(i):
                if not headers[x] == 'plugin' and not headers[x] == 'param':
                    crons[_x][headers[x]] = _i
                elif headers[x] == 'plugin':
                    crons[_x]['do'] = ['--media', _i]
                elif headers[x] == 'param':
                    crons[_x]['do'].append('--param')
                    crons[_x]['do'].append(_i)

        # Guardar el código en el archivo de plugins
        _ui.crons = json.dumps(crons)

    crons = _ui.crons
    if crons:
        result = True

    return render_template(
        'crons.html', 
        result=result,
        crons=crons, 
        request=request.method
    )

# Ruta para editar config y channels un plugin
@app.route('/plugin/<plugin>', methods=['GET', 'POST'])
def plugin(plugin):
    plugins = _ui.plugins
    selected_plugin = list(filter(lambda p: p['name'] == plugin, plugins))
    result = False
    if request.method == 'POST':
        # Obtener los valores del formulario
        config_data = {}
        config_data['config_file'] = '{}/{}/{}'.format(
            './plugins',
            selected_plugin[0]['name'],
            'config.json'
        )
        for key, value in request.form.items():
            config_data[key] = value
        
        _ui.plugins = config_data

        if config_data:
            result = True

        plugins = _ui.plugins
        selected_plugin = list(filter(lambda p: p['name'] == plugin, plugins))
        
    return render_template(
        'plugin_settings.html',
        plugin=selected_plugin[0],
        result=result,
        request=request.method
    )

# Ruta para editar config y channels un plugin
@app.route('/plugin/<plugin>/channels', methods=['GET', 'POST'])
def plugin_channels(plugin):
    result=False
    plugins = _ui.plugins

    selected_plugin = list(filter(lambda p: p['name'] == plugin, plugins))

    if request.method == 'POST':
        # Obtener los valores del formulario
        config_data = {}
        config_data['config_file'] = '{}/{}/{}'.format(
            './plugins',
            selected_plugin[0]['name'],
            'channel_list.json'
        )
        config_data['channels'] = request.form.getlist('channels')
        _ui.plugins = config_data

        if config_data['channels']:
            result = True

        plugins = _ui.plugins
        selected_plugin = list(filter(lambda p: p['name'] == plugin, plugins))

    return render_template(
        'plugin_channels.html',
        plugin=selected_plugin[0],
        result=result,
        request=request.method
    )

"""
@socketio.on('connect')
def on_connect():
    print('ytdlp2STRM IO connected')

@socketio.on('message')
def execute(command): 
    try:
        print(command)
        for path in w.worker(command).run_command():
            print(path)
    except:
        print('except')
        pass     
"""

@socketio.on('execute_command')
def handle_command(command):
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
            process = Popen(shlex.split(command), stdout=PIPE, stderr=PIPE, text=True)

            # Leer y emitir la salida en tiempo real
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    #print(output.strip())  # Debugging: Imprimir en el servidor
                    emit('command_output', output.strip())  # Enviar a cliente

            # Manejar salida de error si existe
            _, stderr = process.communicate()
            if stderr:
                emit('command_error', stderr.strip())

            # Importante: Emitir 'command_completed' al finalizar el comando
            emit('command_completed', {'data': 'Comando completado'})
        else:
            emit('command_output', 'only python cli.py command can be executed from here.')
            emit('command_completed', {'data': 'Comando completado'})
    except:
        emit('command_output', 'only python cli.py command can be executed from here.')
        emit('command_completed', {'data': 'Comando completado'})