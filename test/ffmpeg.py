import ffmpeg

def test_ffmpeg_python_installation():
    """Prueba si ffmpeg está correctamente instalado y accesible a través de ffmpeg-python."""
    try:
        # Intentar ejecutar un comando simple para obtener la versión de FFmpeg
        # Nota: ffmpeg-python no expone directamente la versión de FFmpeg, así que usamos probe con un comando no dañino
        ffmpeg.probe('-', show_error=True, cmd='ffmpeg -version')
        
        print("FFmpeg está correctamente instalado y es accesible a través de ffmpeg-python.")
        return True
        
    except ffmpeg.Error as e:
        # Si ffmpeg.Error es lanzado, algo falló con el acceso a FFmpeg, posiblemente no está instalado
        print("FFmpeg no está instalado o no es accesible a través de ffmpeg-python. Asegúrate de que FFmpeg esté en el PATH.")
        return False

# Llamar a la función para probar si FFmpeg es accesible
test_ffmpeg_python_installation()
