import json
from clases.config import config as c

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