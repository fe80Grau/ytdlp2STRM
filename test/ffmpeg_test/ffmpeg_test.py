import os
import ffmpeg

def image_to_video(image_path, output_video, duration=1):
    """
    Convierte una imagen en un video de X segundos utilizando ffmpeg-python.
    
    :param image_path: Ruta de la imagen.
    :param output_video: Ruta del archivo de video de salida.
    :param duration: Duración del video.
    """
    try:
        (
            ffmpeg
            .input(image_path, loop=1, t=duration, framerate=10)  # utilizar ‘.input’ para definir la fuente y parámetros
            .output(output_video, vcodec='libx264', pix_fmt='yuv420p', movflags='faststart')  # configurar la salida
            .run(overwrite_output=True)  # ejecutar la operación
        )
    except:
        print(
            'Error ffmpeg library not found'
        )

# Uso de la función

path = os.getcwd()
image_to_video(
    os.path.join(path, 'a_black_image.jpg'), 
    os.path.join(path, 'output_video.mp4'), 
    duration=1
)