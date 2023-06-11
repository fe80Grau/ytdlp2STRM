import requests
import re
import webbrowser

# URL de Twitch de donde extraeremos la información
url = "https://www.twitch.tv/revenant/about"

# Realizamos la petición a la página web
response = requests.get(url)

# Obtener el código HTML de la página web
html = response.content
# Escribimos el contenido HTML en un archivo
with open("twitch.html", "wb") as f:
    f.write(html)

# Abrimos el archivo en el navegador web
webbrowser.open("twitch.html")
print(html)

# Expresión regular para encontrar la URL del banner
banner_regex = r"\bhttps.*profile_banner.*\b"

# Buscamos la URL del banner utilizando la expresión regular
banner_url = re.findall(banner_regex, str(html))[0]

# Obtenemos la información de la imagen de perfil
profile_image = re.search(r"class=\"tw-image-avatar\".*?src=\"(.*?)\"", str(html))
profile_image_url = profile_image.group(1)

# Mostramos los resultados obtenidos
print("Banner URL:", banner_url)
print("Profile Image URL:", profile_image_url)