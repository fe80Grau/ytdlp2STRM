##URL GET COOKIE 
#https://boot.pluto.tv/v4/start?appName=web&appVersion=7.4.1-9c652bb3f73b3a4ec5b0a09c668bd63cffe57d94&deviceVersion=114.0.1823&deviceModel=web&deviceMake=edge-chromium&deviceType=web&clientID=790ccc17-b350-4825-a0f8-12e3640752fa&clientModelNumber=1.0.0&episodeSlugs=south-park-es&serverSideAds=false&constraints=&drmCapabilities=widevine%3AL3&blockingMode=&clientTime=2023-07-19T23%3A23%3A01.571Z

# GET SERIE ID FROM .background-image  background-image url burned in html series page code

#CURL SEASON
"""
curl 'https://service-vod.clusters.pluto.tv/v4/vod/series/60f7cd29cd9d6f0013a55912/seasons?offset=1000&page=1' \
  -H 'authority: service-vod.clusters.pluto.tv' \
  -H 'accept: */*' \
  -H 'accept-language: es,es-ES;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6' \
  -H 'authorization: Bearer eyJhbGciOiJIUzI1NiIsImtpZCI6IjViNDAxNjE3LTU0ZTAtNDQwYS04ZTFmLWQ0ZjFjMjhmYjQxMyIsInR5cCI6IkpXVCJ9.eyJzZXNzaW9uSUQiOiJmOTliOGI0YS0yNjhiLTExZWUtOGQyOS1iMmMxNmFkNGI5MzMiLCJjbGllbnRJUCI6Ijc5LjE1NC45Ni4zNiIsImNpdHkiOiJCYXJjZWxvbmEiLCJwb3N0YWxDb2RlIjoiMDgwMjciLCJjb3VudHJ5IjoiRVMiLCJkbWEiOjAsImFjdGl2ZVJlZ2lvbiI6IkVTIiwiZGV2aWNlTGF0Ijo0MS4zODcsImRldmljZUxvbiI6Mi4xNzAxLCJwcmVmZXJyZWRMYW5ndWFnZSI6ImVzIiwiZGV2aWNlVHlwZSI6IndlYiIsImRldmljZVZlcnNpb24iOiIxMTQuMC4xODIzIiwiZGV2aWNlTWFrZSI6ImVkZ2UtY2hyb21pdW0iLCJkZXZpY2VNb2RlbCI6IndlYiIsImFwcE5hbWUiOiJ3ZWIiLCJhcHBWZXJzaW9uIjoiNy40LjEtOWM2NTJiYjNmNzNiM2E0ZWM1YjBhMDljNjY4YmQ2M2NmZmU1N2Q5NCIsImNsaWVudElEIjoiNzkwY2NjMTctYjM1MC00ODI1LWEwZjgtMTJlMzY0MDc1MmZhIiwiY21BdWRpZW5jZUlEIjoiIiwiaXNDbGllbnRETlQiOmZhbHNlLCJ1c2VySUQiOiIiLCJsb2dMZXZlbCI6IkRFRkFVTFQiLCJ0aW1lWm9uZSI6IkV1cm9wZS9NYWRyaWQiLCJzZXJ2ZXJTaWRlQWRzIjpmYWxzZSwiZTJlQmVhY29ucyI6ZmFsc2UsImZlYXR1cmVzIjp7ImlzU3RpdGNoZXJFa3MiOnRydWUsIm11bHRpUG9kQWRzIjp7ImVuYWJsZWQiOnRydWV9fSwiZHJtIjp7Im5hbWUiOiJ3aWRldmluZSIsImxldmVsIjoiTDMifSwiaXNzIjoiYm9vdC5wbHV0by50diIsInN1YiI6InByaTp2MTpwbHV0bzpkZXZpY2VzOkVTOk56a3dZMk5qTVRjdFlqTTFNQzAwT0RJMUxXRXdaamd0TVRKbE16WTBNRGMxTW1aaCIsImF1ZCI6IioucGx1dG8udHYiLCJleHAiOjE2ODk4OTU3MTIsImlhdCI6MTY4OTgwOTMxMiwianRpIjoiN2MwOWEyNzUtNjllMS00MjQ4LTgxMDMtZjU2Njc2Y2UzMzkzIn0.MAIJmLZj1D6M6dJVLQw6BPFsIz0Cn408lyheTQanA9s' \
  -H 'origin: https://pluto.tv' \
  -H 'referer: https://pluto.tv/' \
  -H 'sec-ch-ua: "Not.A/Brand";v="8", "Chromium";v="114", "Microsoft Edge";v="114"' \
  -H 'sec-ch-ua-mobile: ?0' \
  -H 'sec-ch-ua-platform: "Windows"' \
  -H 'sec-fetch-dest: empty' \
  -H 'sec-fetch-mode: cors' \
  -H 'sec-fetch-site: same-site' \
  -H 'user-agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36 Edg/114.0.1823.86' \
  --compressedº
  """


from flask import Flask, stream_with_context, request, Response, send_from_directory, send_file, redirect
from functions import make_clean_folder, write_file, tvinfo_scheme, host, port
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
import wget
import zipfile
import os

session = AsyncHTMLSession()
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
    "Accept-Language": "es-ES,es;q=0.9",
}


source_platform = "pluto_tv"
#Reading config file
config_file = './plugins/pluto_tv/config.json'
if not os.path.isfile(config_file):
    print("No config.json detected, using config.example.json. Please check this in current plugin folder")
    config_file = './plugins/pluto_tv/config.example.json'

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
        channels_list_local = './plugins/pluto_tv/channel_list.example.json'

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
    today = (
        datetime
        .today()
        .strftime("%Y-%m-%d")
    )

    session_token_url = "https://boot.pluto.tv/v4/start?appName=web&appVersion=7.4.1-9c652bb3f73b3a4ec5b0a09c668bd63cffe57d94&deviceVersion=114.0.1823&deviceModel=web&deviceMake=edge-chromium&deviceType=web&clientModelNumber=1.0.0&serverSideAds=false&constraints=&clientid=123&drmCapabilities=widevine%3AL3&blockingMode=&clientTime={}T13%3A23%3A01.571Z".format(
        today
    )
    #print(session_token_url)
    session_token = json.loads(
          requests.get(session_token_url)
          .text
    )
    session_token = session_token['sessionToken']

    download_chromedriver()

    
    chrome_options = Options()
    chrome_options.add_argument("--log-level=3")  # Ejecutar en modo headless para no abrir una ventana del navegador
    chrome_options.add_argument("--disable-gpu")  # Ejecutar en modo headless para no abrir una ventana del navegador
    chrome_options.add_argument("--headless")  # Ejecutar en modo headless para no abrir una ventana del navegador
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    def get_episode_id(channel):
        driver = webdriver.Chrome(executable_path='bin/chromedriver.exe', options=chrome_options)
        driver.get(channel)
        wait = WebDriverWait(driver, 15)
        wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, '.episode-container-atc')
            )
        )
        #html_renderizado = driver.page_source
        element = driver.find_element(
            By.CSS_SELECTOR,
            ".episode-container-atc"
        )

        #with open("test.html", "w", encoding='utf-8') as f:
        #    f.write(driver.page_source)

        episode_url = (
            element
            .find_element(By.CSS_SELECTOR, "a")
            .get_attribute("href")
        )
      
        driver.quit()

        return episode_url
    
    def get_seasson_id(episode_url):
        driver = webdriver.Chrome(executable_path='bin/chromedriver.exe', options=chrome_options)
        driver.get(episode_url)
        #html_renderizado = driver.page_source
        wait = WebDriverWait(driver, 15)
        wait.until(
            EC.presence_of_element_located(
                (By.XPATH, "//meta[@property='og:image']")
            )
        )

        with open("test.html", "w", encoding='utf-8') as f:
            f.write(driver.page_source)


        seasson_id = driver.find_element(
            By.XPATH, "//meta[@property='og:image']"
        )

        print(seasson_id.get_attribute('content'))


        driver.quit()

        return seasson_id

    for channel in channels():
        episode_url = get_episode_id(channel)
        print(episode_url)

        seasson_id = get_seasson_id(episode_url)

        print(seasson_id)


def direct(pluto_tv_id): #Sponsorblock doesn't work in this mode
    pass

