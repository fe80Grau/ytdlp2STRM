FROM python:3.9
WORKDIR /opt/ytdlp2STRM

COPY . /opt/ytdlp2STRM
ENV AM_I_IN_A_DOCKER_CONTAINER Yes
ENV DOCKER_PORT 5005

# Actualizar el sistema e instalar dependencias del sistema
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    libxml2-dev \
    libxslt1-dev \
    ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Instalar paquetes Python previamente, para permitir el uso de ruedas precompiladas
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir lxml

# Instalar los requisitos del proyecto, incluyendo nuevamente lxml
RUN pip install --no-cache-dir --upgrade -r /opt/ytdlp2STRM/requeriments.txt

EXPOSE 5000

CMD ["python", "main.py"]