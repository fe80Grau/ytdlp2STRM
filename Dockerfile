FROM python:3.9
WORKDIR /opt/ytdlp2STRM
COPY . /opt/ytdlp2STRM
ENV AM_I_IN_A_DOCKER_CONTAINER Yes
ENV DOCKER_PORT 5005
RUN pip install --no-cache-dir --upgrade -r /opt/ytdlp2STRM/requierments.txt
CMD ["python", "main.py"]
EXPOSE 5000