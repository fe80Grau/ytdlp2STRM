from seleniumbase import Driver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
import time
import pandas as pd

def to_strm(param):
    # Initializing the Chrome service
    driver = Driver(uc=True)

    # Opening the Crunchyroll page
    driver.get('https://www.crunchyroll.com/fr/videos/alphabetical')

    # Waiting for the page to load completely
    time.sleep(3)

    # Scroll down until the footer is reached
    body = driver.find_element("tag name", "body")
    links = set()

    def is_footer_visible():
        return driver.execute_script('''
            let footer = document.querySelector('.erc-footer');
            let rect = footer.getBoundingClientRect();
            return (
                Math.floor(rect.bottom) <= window.innerHeight &&
                rect.top >= 0
            );
        ''')

    while not is_footer_visible():
        body.send_keys(Keys.PAGE_DOWN)
        time.sleep(1)  # Waiting time for loading, adjustable if needed
        new_links = driver.execute_script('''
        let links = document.querySelectorAll('a');
        return Array.from(links)
            .filter(link => link.href.startsWith('https://www.crunchyroll.com/fr/series/') && !link.title.includes('VOSTA'))
            .map(link => link.href);
        ''')
        links.update(new_links)

    # Closing the browser
    driver.quit()
    links_df = pd.DataFrame(links, columns=['URL']).drop_duplicates()
    # Extract last segment in url (by slash)
    links_df['Last_Segment'] = links_df['URL'].apply(lambda x: x.split('/')[-1])
    # Sort by 'Last_Segment'
    df_sorted = links_df.sort_values('Last_Segment')
    # URL list sorted to_csv
    df_sorted['URL'].to_csv('liens.csv', index=False, header=False)


    return True
