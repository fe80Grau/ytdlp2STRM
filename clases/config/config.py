import json
import os
import shutil

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
                print(f"No {self.config_file} detected, Building a copy from {example_config_file}. Please check this in config folder")
                shutil.copyfile(
                    example_config_file, 
                    self.config_file
                )

                # Leer el archivo de ejemplo de configuración JSON
                with open(self.config_file, "r") as file:
                    config_data = json.load(file)
            else:
                #print(f"No config.json or config.example.json detected in config folder: {self.config_file}")
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
                print(f"No {self.config_file} detected, Building a copy from {example_config_file}. Please check this in config folder")
                shutil.copyfile(
                    example_config_file, 
                    self.config_file
                )

                # Leer el archivo de ejemplo de configuración JSON
                with open(self.config_file, "r") as file:
                    config_data = json.load(file)
            else:
                #print(f"No channles.json or channel_list.example.json detected in config folder: {self.config_file}")
                return None

        return config_data