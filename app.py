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

# Initialize FastAPI
app = FastAPI()

# Global variables for storing scraped data and status
gps_data = None
alarm_data = None
status = {
    "logged_in": False,
    "online": False,
    "errors": None,
    "scraping_attempts": 0,
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
    global status
    try:
        driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=chrome_options)
        driver.get("https://example.com/login")  # Replace with the actual URL
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "changBar0"))
        ).click()

        # Fill login fields and submit
        username = driver.find_element(By.ID, "txtUserName")
        password = driver.find_element(By.ID, "txtAccountPassword")
        username.send_keys("your_username")  # Replace with actual username
        password.send_keys("your_password")  # Replace with actual password
        driver.find_element(By.ID, "btnLogin").click()

        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.ID, "pageShowCanvas_Map"))  # Adjust to a specific element post-login
        )

        status["logged_in"] = True
        status["online"] = True
        status["last_action"] = "Logged in successfully"
        return driver
    except Exception as e:
        status["logged_in"] = False
        status["errors"] = f"Login failed: {str(e)}"
        status["last_failure_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status["last_action"] = "Login attempt failed"
        status["login_attempts"] += 1
        return None

# Function to scrape GPS data
def scrape_gps_data(driver):
    global gps_data, status
    try:
        gps_table = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "divDevicesListInfo"))
        )
        rows = gps_table.find_elements(By.TAG_NAME, "tr")
        gps_data_list = []
        for row in rows[1:]:
            cols = row.find_elements(By.TAG_NAME, "td")
            if len(cols) == 11:
                gps_data_entry = {
                    "Target Name": cols[0].text.strip(),
                    "Type": cols[1].text.strip(),
                    "License Plate No.": cols[2].text.strip(),
                    "Speed Limit": cols[3].text.strip(),
                    "Latitude": cols[4].text.strip(),
                    "Longitude": cols[5].text.strip(),
                    "Speed": cols[6].text.strip(),
                    "Direction": cols[7].text.strip(),
                    "Total mileage": cols[8].text.strip(),
                    "Status": cols[9].text.strip(),
                    "Position time": cols[10].text.strip()
                }
                gps_data_list.append(gps_data_entry)

        gps_data = json.dumps(gps_data_list, indent=4)
        status["scraping_attempts"] += 1
        status["last_action"] = "GPS data scraped successfully"
        status["errors"] = None
    except Exception as e:
        status["errors"] = f"Failed to scrape GPS data: {str(e)}"
        status["last_failure_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status["last_action"] = "Scraping GPS data failed"

# Function to scrape Alarm data
def scrape_alarm_data(driver):
    global alarm_data, status
    try:
        alarm_table = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "divExceptionMessageDivInfo"))
        )
        rows = alarm_table.find_elements(By.TAG_NAME, "tr")
        alarm_data_list = []
        for row in rows[1:]:
            cols = row.find_elements(By.TAG_NAME, "td")
            if len(cols) == 7:
                alarm_data_entry = {
                    "Target Name": cols[0].text.strip(),
                    "ID No.": cols[1].text.strip(),
                    "Alarm Type": cols[2].text.strip(),
                    "Alarm Time": cols[3].text.strip(),
                    "Position Time": cols[4].text.strip(),
                    "Type": cols[5].text.strip(),
                    "Operate": "Clear"
                }
                alarm_data_list.append(alarm_data_entry)

        alarm_data = json.dumps(alarm_data_list, indent=4)
        status["scraping_attempts"] += 1
        status["last_action"] = "Alarm data scraped successfully"
        status["errors"] = None
    except Exception as e:
        status["errors"] = f"Failed to scrape Alarm data: {str(e)}"
        status["last_failure_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status["last_action"] = "Scraping Alarm data failed"

# Function to continuously scrape GPS and Alarm data
def continuous_scrape():
    while True:
        if not status["logged_in"]:
            driver = perform_login()
        if status["logged_in"]:
            scrape_gps_data(driver)
            scrape_alarm_data(driver)
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
    if status["logged_in"]:
        driver.save_screenshot("screenshot.png")
        return {"message": "Screenshot taken"}
    return {"error": "Not logged in"}

# Start the continuous scraping in a separate thread
import threading
scraping_thread = threading.Thread(target=continuous_scrape)
scraping_thread.daemon = True
scraping_thread.start()
