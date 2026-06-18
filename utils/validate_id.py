"""
Validacion de identificadores recibidos por las rutas web.

Estos IDs (youtube_id, twitch_id, crunchyroll_id, ...) se acaban pasando
como argumentos a yt-dlp / herramientas externas. Para evitar la inyeccion
de argumentos (p. ej. un ID que empiece por '-' seria interpretado por
yt-dlp como una opcion del tipo --exec) se restringe el conjunto de
caracteres permitidos y se prohibe que el valor comience por '-'.
"""
import re

# Solo letras, numeros, guion bajo, guion y punto. Suficiente para los IDs
# legitimos de YouTube, Twitch y Crunchyroll. Los IDs validos nunca empiezan
# por '-', asi que ese caso se rechaza explicitamente mas abajo.
_ALLOWED_ID_RE = re.compile(r'^[A-Za-z0-9_.-]+$')


def is_valid_media_id(value, max_length=128):
    """Devuelve True si `value` es un identificador seguro para pasar a yt-dlp."""
    if not isinstance(value, str):
        return False
    if not value or len(value) > max_length:
        return False
    # Impide que el valor sea interpretado como una opcion de linea de comandos.
    if value.startswith('-'):
        return False
    return bool(_ALLOWED_ID_RE.match(value))
