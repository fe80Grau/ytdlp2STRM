import json
import os

class config:
    def __init__(self, config_file):
        self.config_file = config_file

    def get_config(self):
        # Comprobar si existe el archivo de configuración
        if os.path.exists(self.config_file):
            # Leer el archivo de configuración JSON
            with open(self.config_file, "r") as file:
                config_data = json.load(file)
        else:
            # Generar el nombre del archivo de ejemplo
            example_config_file = os.path.splitext(self.config_file)[0] + ".example.json"

            # Comprobar si existe el archivo de ejemplo
            if os.path.exists(example_config_file):
                print("No config.json detected, using config.example.json. Please check this in config folder")

                # Leer el archivo de ejemplo de configuración JSON
                with open(example_config_file, "r") as file:
                    config_data = json.load(file)
            else:
                print(f"No config.json or config.example.json detected in config folder: {self.config_file}")
                return None

        return config_data
    
    def get_channels(self):
        # Comprobar si existe el archivo de configuración
        if os.path.exists(self.config_file):
            # Leer el archivo de configuración JSON
            with open(self.config_file, "r") as file:
                config_data = json.load(file)
        else:
            # Generar el nombre del archivo de ejemplo
            example_config_file = os.path.splitext(self.config_file)[0] + ".example.json"

            # Comprobar si existe el archivo de ejemplo
            if os.path.exists(example_config_file):
                print("No channles.json detected, using channles.example.json. Please check this in config folder")

                # Leer el archivo de ejemplo de configuración JSON
                with open(example_config_file, "r") as file:
                    config_data = json.load(file)
            else:
                print(f"No channles.json or channles.example.json detected in config folder: {self.config_file}")
                return None

        return config_data