import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import re
from urllib.parse import urljoin
import time
from tqdm import tqdm
import logging
import requests
from selenium.common.exceptions import WebDriverException

# Browser header configurations (updated versions)
BROWSER_HEADERS = {
    'chrome': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
    },
    'firefox': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
    },
    'safari': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
    },
    'edge': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.2365.63',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
    }
}

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)

file_handler = logging.FileHandler('cyberdrop_downloader.log')
file_handler.setLevel(logging.ERROR)
file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.ERROR)
console_formatter = logging.Formatter('%(levelname)s: %(message)s')
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)

def setup_driver(browser='firefox', headless=True):
    """Set up Selenium WebDriver with browser-specific options"""
    try:
        if browser == 'chrome':
            chrome_options = ChromeOptions()
            if headless:
                chrome_options.add_argument("--headless=new")  # Updated to new headless mode
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--enable-unsafe-swiftshader")
            chrome_options.add_argument("--disable-gpu-compositing")
            chrome_options.add_argument("--disable-accelerated-2d-canvas")
            chrome_options.add_argument("--disable-software-rasterizer")
            chrome_options.add_argument("--disable-webgl")
            chrome_options.add_argument("--disable-features=UseSkiaRenderer")
            chrome_options.add_argument("--disable-gpu-sandbox")
            chrome_options.add_argument("--disable-renderer-backgrounding")
            chrome_options.add_argument("--enable-logging")
            chrome_options.add_argument("--v=1")
            chrome_options.add_argument(f"user-agent={BROWSER_HEADERS[browser]['User-Agent']}")
            driver = webdriver.Chrome(options=chrome_options)
        else:  # Default to Firefox
            firefox_options = FirefoxOptions()
            if headless:
                firefox_options.add_argument("--headless")
            firefox_options.add_argument(f"- MOZ_USER_AGENT={BROWSER_HEADERS[browser]['User-Agent']}")
            driver = webdriver.Firefox(options=firefox_options)
        return driver
    except WebDriverException as e:
        error_msg = f"Failed to initialize WebDriver for {browser}: {str(e)}"
        print(error_msg)
        logger.error(error_msg)
        return None

def solve_captcha(album_url, browser='firefox'):
    """Manually solve CAPTCHA by opening a visible browser"""
    try:
        driver = setup_driver(browser, headless=False)
        if not driver:
            return None
        driver.get(album_url)
        
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "g-recaptcha"))
        )
        print("CAPTCHA detected! Please solve it in the browser window.")
        input("Press Enter after solving the CAPTCHA...")
        
        return driver
        
    except Exception as e:
        error_msg = f"Manual CAPTCHA solving failed: {str(e)}"
        print(error_msg)
        logger.error(error_msg)
        return None

def download_file(url, folder, retries=3):
    filename = url.split('/')[-1]
    filepath = os.path.join(folder, filename)
    
    if os.path.exists(filepath):
        print(f"Skipping {filename} - already downloaded")
        return True
    
    for attempt in range(retries):
        try:
            headers = BROWSER_HEADERS['firefox']  # Default to Firefox headers
            response = requests.get(url, headers=headers, stream=True, timeout=10)
            response.raise_for_status()
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            print(f"Downloaded {filename}")
            return True
            
        except Exception as e:
            error_msg = f"Attempt {attempt + 1}/{retries} failed for {filename}: {str(e)}"
            print(f"\n{error_msg}")
            logger.error(error_msg)
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            else:
                final_msg = f"Failed to download {filename} after {retries} attempts"
                print(final_msg)
                logger.error(final_msg)
                return False

def get_album_files(album_url, driver, browser='firefox'):
    try:
        driver.get(album_url)
        
        try:
            if driver.find_elements(By.ID, "g-recaptcha"):
                driver.quit()
                driver = solve_captcha(album_url, browser)
                if not driver:
                    return []
        except Exception as e:
            error_msg = f"CAPTCHA detection error: {str(e)}"
            print(error_msg)
            logger.error(error_msg)
            return []
        
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "a"))
        )
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        file_links = []
        for link in soup.find_all('a', href=True):
            href = link['href']
            if re.search(r'\.(jpg|jpeg|png|gif|mp4|zip|rar|pdf)$', href, re.IGNORECASE):
                full_url = urljoin(album_url, href)
                file_links.append(full_url)
        return file_links
        
    except Exception as e:
        error_msg = f"Error accessing album {album_url}: {str(e)}"
        print(error_msg)
        logger.error(error_msg)
        return []

def download_cyberdrop_album(album_url, download_path="downloads", browser='firefox'):
    driver = setup_driver(browser, headless=True)
    if not driver:
        print("WebDriver setup failed, aborting.")
        return
    
    if not os.path.exists(download_path):
        os.makedirs(download_path)
    
    print(f"Fetching album: {album_url} (emulating {browser})")
    file_urls = get_album_files(album_url, driver, browser)
    
    driver.quit()
    
    if not file_urls:
        print("No files found or error occurred")
        return
    
    print(f"Found {len(file_urls)} files to download")
    
    with tqdm(total=len(file_urls), desc="Downloading", unit="file") as pbar:
        for file_url in file_urls:
            success = download_file(file_url, download_path)
            pbar.update(1)
            if success:
                time.sleep(1)
    
    print("\nDownload complete!")

if __name__ == "__main__":
    album_url = input("Enter the Cyberdrop.me album URL: ")
    download_path = input("Enter download directory (press Enter for 'downloads'): ") or "downloads"
    browser_choice = input("Choose browser to emulate (firefox/chrome/safari/edge, default=firefox): ").lower() or 'firefox'
    if browser_choice not in BROWSER_HEADERS:
        print(f"Invalid choice, defaulting to firefox")
        browser_choice = 'firefox'
    
    download_cyberdrop_album(album_url, download_path, browser_choice)