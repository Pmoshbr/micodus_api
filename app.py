import time
import json
from datetime import datetime
from fastapi import FastAPI
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import threading

# Load config.json for credentials and settings
with open("config.json") as f:
    config = json.load(f)

# Initialize FastAPI
app = FastAPI()

# Global variables for storing scraped data and status
gps_data = None
alarm_data = None
driver = None
scrape_attempts_gps = 0
scrape_attempts_alarm = 0
login_attempts = 0
status = {
    "logged_in": False,
    "online": False,
    "errors": None,
    "scraping_attempts_gps": 0,
    "scraping attempts_alarm": 0,
    "login_attempts": 0,
    "last_action": "",
    "last_failure_time": None,
}

# Chrome WebDriver options for headless execution
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")

# Function to perform login
def perform_login():
    global status, driver, login_attempts

    try:
        if login_attempts >= config["max_login_attempts"]:
            status["errors"] = "Max login attempts reached"
            return None

        # Setup WebDriver if it's not already initialized
        if driver is None:
            driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=chrome_options)

        driver.get(config["url_login"])
        WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.ID, "changBar0"))).click()
        status["online"] = True
        status["last_action"] = "Change login type"

        # Fill login fields and submit
        username = driver.find_element(By.ID, "txtUserName")
        password = driver.find_element(By.ID, "txtAccountPassword")
        username.send_keys(config["login"])  # Use username from config.json
        password.send_keys(config["password"])  # Use password from config.json
        status["last_action"] = "Click to Login Button"
        driver.find_element(By.ID, "btnLogin").click()

        # Wait until the page loads
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, "form1")))
        status["last_action"] = "Login Successul"

        iframe_element = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//div[@id='pageShowCanvas_Map']//iframe")))
        iframe_url = iframe_element.get_attribute("src")
        status["last_action"] = "URL Redirect: " + iframe_url
        driver.get(iframe_url)

        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, "divDevicesList")))

        status["logged_in"] = True
        status["online"] = True
        status["last_action"] = "Logged in successfully"
        login_attempts = 0
        status["login_attempts"] = login_attempts
        return driver
    except Exception as e:
        login_attempts += 1
        status["logged_in"] = False
        status["errors"] = f"Login failed: {str(e)}"
        status["last_failure_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status["last_action"] = "Login attempt failed"
        return None

# Function to scrape GPS data
def scrape_gps_data(driver):
    global gps_data, status, scrape_attempts_gps
    try:
        # Aguardar a presença do div que contém a tabela com as informações do GPS
        gps_table_div = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.ID, "divDevicesListInfo"))
        )

        # Buscar a tabela dentro do div identificado
        table = gps_table_div.find_element(By.TAG_NAME, "table")
        rows = table.find_elements(By.TAG_NAME, "tr")
        
        gps_data_list = []
        for row in rows[1:]:
            cols = row.find_elements(By.TAG_NAME, "td")
            if len(cols) == 11:
                gps_data_entry = {
                    "Target Name": cols[0].get_attribute("innerText").strip(),
                    "Type": cols[1].get_attribute("innerText").strip(),
                    "License Plate No.": cols[2].get_attribute("innerText").strip(),
                    "Speed Limit": cols[3].get_attribute("innerText").strip(),
                    "Latitude": cols[4].get_attribute("innerText").strip(),
                    "Longitude": cols[5].get_attribute("innerText").strip(),
                    "Speed": cols[6].get_attribute("innerText").strip(),
                    "Direction": cols[7].get_attribute("innerText").strip(),
                    "Total mileage": cols[8].get_attribute("innerText").strip(),
                    "Status": cols[9].get_attribute("innerText").strip(),
                    "Position time": cols[10].get_attribute("innerText").strip()
                }
                gps_data_list.append(gps_data_entry)

        gps_data = json.dumps(gps_data_list, indent=4)
        scrape_attempts_gps = 0
        status["scraping_attempts_gps"] = scrape_attempts_gps
        status["last_action"] = "GPS data scraped successfully"
        status["errors"] = None
    except Exception as e:
        scrape_attempts_gps += 1
        status["scraping_attempts_gps"] = scrape_attempts_gps
        status["errors"] = f"Failed to scrape GPS data: {str(e)}"
        status["last_failure_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status["last_action"] = "Scraping GPS data failed"

# Function to scrape Alarm data
def scrape_alarm_data(driver):
    global alarm_data, status, scrape_attempts_alarm
    try:
        alarm_table = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.ID, "divExceptionMessageDivInfo"))
        )
        rows = alarm_table.find_elements(By.TAG_NAME, "tr")
        alarm_data_list = []
        for row in rows[1:]:
            cols = row.find_elements(By.TAG_NAME, "td")
            if len(cols) == 7:
                alarm_data_entry = {
                    "Target Name": cols[0].get_attribute("innerText").strip(),
                    "ID No.": cols[1].get_attribute("innerText").strip(),
                    "Alarm Type": cols[2].get_attribute("innerText").strip(),
                    "Alarm Time": cols[3].get_attribute("innerText").strip(),
                    "Position Time": cols[4].get_attribute("innerText").strip(),
                    "Type": cols[5].get_attribute("innerText").strip()
                }
                alarm_data_list.append(alarm_data_entry)

        alarm_data = json.dumps(alarm_data_list, indent=4)
        scrape_attempts_alarm = 0
        status["scraping_attempts_alarm"] = scrape_attempts_alarm
        status["last_action"] = "Alarm data scraped successfully"
        status["errors"] = None
    except Exception as e:
        scrape_attempts_alarm += 1
        status["scraping_attempts_alarm"] = scrape_attempts_alarm
        status["errors"] = f"Failed to scrape Alarm data: {str(e)}"
        status["last_failure_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status["last_action"] = "Scraping Alarm data failed"

# Function to continuously scrape GPS and Alarm data
def continuous_scrape():
    global scrape_attempts_gps, scrape_attempts_alarm
    while True:
        if not status["logged_in"]:
            driver = perform_login()
        if status["logged_in"]:
            scrape_gps_data(driver)
            #scrape_alarm_data(driver)
            if scrape_attempts_gps >= config["max_scrape_attempts"]:
                status["errors"] = "Max scraping attempts GPS reached"
                break
            if scrape_attempts_alarm >= config["max_scrape_attempts"]:
                status["errors"] = "Max scraping attempts Alarm reached"
                break
        time.sleep(10)  # Scrape every 10 seconds

# FastAPI route to get GPS data
@app.get("/gps")
def get_gps_data():
    if gps_data:
        return json.loads(gps_data)
    return {"error": "No GPS data available"}

# FastAPI route to get Alarm data
@app.get("/alarms")
def get_alarm_data():
    if alarm_data:
        return json.loads(alarm_data)
    return {"error": "No alarm data available"}

# FastAPI route to get the status
@app.get("/status")
def get_status():
    return status

# FastAPI route to take a screenshot
@app.get("/screenshot")
def take_screenshot():
    global driver
    if driver:
        driver.save_screenshot("screenshot.png")
        return {"message": "Screenshot taken"}
    return {"error": "Driver not initialized"}

# Start the continuous scraping in a separate thread
scraping_thread = threading.Thread(target=continuous_scrape)
scraping_thread.daemon = True
scraping_thread.start()
