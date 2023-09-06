FROM python:3.9
WORKDIR /opt/ytdlp2STRM
COPY . /opt/ytdlp2STRM
RUN pip install --no-cache-dir --upgrade -r /opt/ytdlp2STRM/requierments.txt
CMD ["python", "main.py"]