from __main__ import app
from flask import request, render_template, session, send_from_directory, jsonify
from flask_socketio import SocketIO
import json
import logging
from clases.worker import worker as w
from ui.ui import Ui
_ui = Ui()
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
logging.getLogger('werkzeug').setLevel(logging.WARNING)

# Ruta principal
@app.route('/')
def index():
    crons = _ui.crons
    last_executions = _ui.get_last_executions()
    next_executions = _ui.get_next_executions()
    return render_template(
        'index.html',
        plugins=_ui.plugins,
        crons=crons,
        last_executions=last_executions,
        next_executions=next_executions
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

@app.route('/log')
def view_log():
    log_file = 'ytdlp2strm.log'
    try:
        log_content = []
        with open(log_file, 'r', encoding='utf-8') as file:
            for line in file:
                # Si la línea empieza con '[', formatear el texto dentro de los primeros corchetes
                if line.startswith('['):
                    end_idx = line.find(']')
                    if end_idx != -1:
                        formatted_line = '[<span style="color:yellowgreen;">' + line[1:end_idx] + '</span>]' + line[end_idx+1:]
                    else:
                        formatted_line = line  # Si no hay un cierre de corchete, deja la línea como está
                else:
                    formatted_line = line
                # Añadir un <br/> al final de cada línea
                log_content.append(formatted_line)
        return render_template('log.html', log_content=log_content)
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@socketio.on('connect')
def handle_connect():
    # Enviar el historial del CLI al cliente que se acaba de conectar
    from ui.ui import Ui
    for line in Ui.cli_history:
        socketio.emit('command_output', line)
    # Enviar el estado de ejecución actual
    socketio.emit('execution_status', {'is_running': Ui.is_running})

@socketio.on('execute_command')
def handle_command(command):
    _ui.handle_command(command)