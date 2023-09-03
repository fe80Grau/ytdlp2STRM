from __main__ import app
from flask import request, render_template
import json

config_file = 'config/config.json'
plugins_file = 'config/plugins.py'

# Ruta principal
@app.route('/')
def index():
    return render_template('index.html')

# Ruta para las opciones generales
@app.route('/general', methods=['GET', 'POST'])
def general_options():
    result = False
    if request.method == 'POST':
        # Obtener los valores del formulario
        config_data = {}
        for key, value in request.form.items():
            config_data[key] = value

        # Guardar los valores en el archivo de configuración
        with open(config_file, 'w') as file:
            json.dump(config_data, file)
            result = True

    # Leer el archivo de configuración
    with open(config_file, 'r') as file:
        config_data = json.load(file)

    return render_template('general_options.html', config_data=config_data, result=result, request=request.method)

# Ruta para la edición de plugins
@app.route('/plugins', methods=['GET', 'POST'])
def plugin_options():
    if request.method == 'POST':
        # Obtener el código de plugins desde el formulario
        plugin_code = request.form.get('plugin_code')

        # Guardar el código en el archivo de plugins
        with open(plugins_file, 'w') as file:
            file.write(plugin_code)

    # Leer el archivo de plugins
    with open(plugins_file, 'r') as file:
        plugin_code = file.read()

    return render_template('plugin_options.html', plugin_code=plugin_code)