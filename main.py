from flask import Flask, stream_with_context, request, Response, send_from_directory, send_file, redirect
from threading import Thread
from functions import host, port, clean_old_videos
import subprocess
import time
import json
import urllib.request
import urllib.error
import os
app = Flask(__name__)
import config.routes


if __name__ == "__main__":
    #Thread for clean_old_videos
    thread = Thread(target=clean_old_videos)
    #Set as daemon to keep run behavior sync with main thread (by default)
    thread.daemon = True
    thread.start()
    #Run Flask server
    app.run(host='0.0.0.0',port=port)
