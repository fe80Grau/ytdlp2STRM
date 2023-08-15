from flask import Flask, stream_with_context, request, Response, send_from_directory, send_file, redirect
from functions import make_clean_folder, write_file, write_binary_file, tvinfo_scheme, host, port
from sanitize_filename import sanitize
import os
import json
import time
import re
import platform
import subprocess
import fnmatch
import xml.etree.ElementTree as ET
import requests
from isodate import parse_duration
from bs4 import BeautifulSoup
from datetime import datetime
from requests_html import HTMLSession, AsyncHTMLSession
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from seleniumwire import webdriver as wd  # Import seleniumwire
from vtt_to_srt.vtt_to_srt import ConvertFile

import wget
import zipfile
import os

session = AsyncHTMLSession()
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
    "Accept-Language": "es-ES,es;q=0.9",
}


source_platform = "pandrama"
#Reading config file
config_file = './plugins/pandrama/config.json'
if not os.path.isfile(config_file):
    print("No config.json detected, using config.example.json. Please check this in current plugin folder")
    config_file = './plugins/pandrama/config.example.json'

with open(
        config_file, 
        'r'
    ) as f:
    config = json.load(f)

media_folder = config["strm_output_folder"]
channels_list = config["channels_list_file"]

def channels():
    channels_list_local = channels_list

    if not os.path.isfile(channels_list_local):
        print("No channel_list.json detected, using channel_list.example.json. Please check this in current plugin folder")
        channels_list_local = './plugins/pandrama/channel_list.example.json'

    with open(
            channels_list_local, 
            'r'
        ) as f:
        channels = json.load(f)
    return channels

def to_nfo(params):
    pass

def download_chromedriver():
  # get the latest chrome driver version number
  url = 'https://chromedriver.storage.googleapis.com/LATEST_RELEASE'
  response = requests.get(url)
  version_number = response.text

  # build the donwload url
  download_url = "https://chromedriver.storage.googleapis.com/" + version_number +"/chromedriver_win32.zip"

  # download the zip file using the url built above
  latest_driver_zip = wget.download(download_url,'temp/chromedriver.zip')

  # extract the zip file
  with zipfile.ZipFile(latest_driver_zip, 'r') as zip_ref:
      zip_ref.extractall('bin') # you can specify the destination folder path here
  # delete the zip file downloaded above
  os.remove(latest_driver_zip)

def to_strm(method):
    download_chromedriver()
    mobile_emulation = { "deviceName": "iPhone SE" }

    chrome_options = Options()
    chrome_options.add_argument("--log-level=3")  # Ejecutar en modo headless para no abrir una ventana del navegador
    #chrome_options.add_argument("--disable-gpu")  # Ejecutar en modo headless para no abrir una ventana del navegador
    #chrome_options.add_argument("--headless")  # Ejecutar en modo headless para no abrir una ventana del navegador
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    #chrome_options.add_experimental_option("mobileEmulation", mobile_emulation)
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--disable-popup-blocking")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
    chrome_options.add_experimental_option("excludeSwitches", ['enable-automation'])


    #chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36')

    def get_episodes(channel):
        episodes_list = []
        
        driver = webdriver.Chrome(
            executable_path='bin/chromedriver.exe', 
            options=chrome_options
        )
        driver.set_window_size(375, 667)
        driver.get(channel)
        driver.implicitly_wait(3)
        #html_renderizado = driver.page_source
        elements = driver.find_element(
            By.CSS_SELECTOR,
            "#hl-plays-list"
        )
        
        elements = elements.find_elements(
            By.CSS_SELECTOR,
            "li"
        )

        for element in elements:
            episode_url = (
                element
                .find_element(By.CSS_SELECTOR, "a")
                .get_attribute("href")
            )
            episodes_list.append(episode_url)
        
        driver.quit()

        return episodes_list

    def get_episode_video_url(episode_url):
        # Create the Chrome driver
        print(episode_url)
        chrome_options.add_experimental_option("mobileEmulation", mobile_emulation)
        driver = wd.Chrome(executable_path='bin/chromedriver.exe', options=chrome_options)
        #driver.accept_untrusted_certs = True
        # Go to the Github homepage
        driver.get(episode_url)
        driver.implicitly_wait(3)
        driver.navigate().refresh()
        driver.implicitly_wait(3)
        driver.switch_to.frame(
            driver.find_element(
                By.CSS_SELECTOR,
                "#playleft iframe"
            )
        )
        driver.implicitly_wait(120)

        element = driver.find_element(
            By.CSS_SELECTOR, 
            ".jw-icon-display"
        )
        driver.execute_script("arguments[0].click();", element)

        episode_mpd = {
            "mpd" : "",
            "subs" : []
        }

        # Access requests list via the `requests` attribute
        for request in driver.requests:
            if request.response:
                if ('mpd' in request.url
                    and 'dash' in request.url):
                    episode_mpd['mpd'] = request.url

                if ('.vtt' in request.url
                    and 'es' in request.url):
                    episode_mpd['subs'].append({"lang" : "es", "url" : request.url})

                if ('.vtt' in request.url
                    and 'en' in request.url):
                    episode_mpd['subs'].append({"lang" : "en", "url" : request.url})

        return episode_mpd
    
    def get_subs(pandrama_channel_folder, sn, video_name, subs_url, subs_lang):
        file_content = requests.get(subs_url, allow_redirects=True).content
        file_path = "{}/{}/{}/{}.{}.{}".format(media_folder,  sanitize("{}".format(pandrama_channel_folder)),  sanitize("Season {}".format(sn)), sanitize(video_name), subs_lang, "vtt")
        
        write_binary_file(file_path, file_content)

        convert_file = ConvertFile(file_path, "utf-8")
        convert_file.convert()

    for channel in channels():
        pandrama_channel_folder = channel.split('/')[-2]
        #Make a folder and inflate nfo file
        make_clean_folder(
            "{}/{}".format(
                media_folder,
                sanitize(
                    "{}".format(
                        pandrama_channel_folder
                    )
                )
            )
        )
        episodes = get_episodes(channel)
        for episode in episodes:
            
            sn = episode.split('-capitulo')[0].split('-')[-1].replace('t','').zfill(2)
            e = episode.split('/')[-2].split('-')[-1].zfill(2)

            video_name = "{} - {}".format("S{}E{}".format(sn, e), "Episodio {}".format(e))

            episode_data = get_episode_video_url(episode)
            file_content = episode_data['mpd']
            file_path = "{}/{}/{}/{}.{}".format(media_folder,  sanitize("{}".format(pandrama_channel_folder)),  sanitize("Season {}".format(sn)), sanitize(video_name), "strm")
            
            make_clean_folder("{}/{}/{}".format(media_folder,  sanitize("{}".format(pandrama_channel_folder)),  sanitize("Season {}".format(sn))))
            
            data = {
                "video_name" : video_name
            }
            if not os.path.isfile(file_path):
                write_file(file_path, file_content)
                for subs in episode_data['subs']:
                    get_subs(pandrama_channel_folder, sn, video_name, subs['url'], subs['lang'])



def direct(pluto_tv_id): #Sponsorblock doesn't work in this mode
    pass

