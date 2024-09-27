import time
from datetime import datetime
from threading import Thread
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from fastapi import FastAPI
import json
import os

app = FastAPI()

# Load configuration from config.json
with open("config.json") as config_file:
    config = json.load(config_file)

status = {
    "logged_in": False,
    "online": False,
    "errors": None,
    "scraping_attempts": 0,
    "login_attempts": 0,
    "last_action": "",
    "last_failure_time": None
}

gps_data = None
alarm_data = None

# Helper function to capture a screenshot during the login process
def capture_screenshot(driver, name="screenshot"):
    screenshot_path = os.path.join(os.getcwd(), f"{name}.png")
    driver.save_screenshot(screenshot_path)
    print(f"Screenshot saved to {screenshot_path}")

# Function to perform login and return a WebDriver instance
def perform_login():
    global status
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=chrome_options)
    driver.get(config["url_login"])

    try:
        # Switch login type
        status["last_action"] = "Login type switched"
        switch_login_type = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "changBar0"))
        )
        switch_login_type.click()

        # Enter credentials
        username_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "txtUserName"))
        )
        password_input = driver.find_element(By.ID, "txtAccountPassword")

        username_input.send_keys(config["login"])
        password_input.send_keys(config["password"])

        # Click login button
        login_button = driver.find_element(By.ID, "btnLogin")
        login_button.click()

        # Wait for the presence of a logged-in-specific element to confirm login
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.ID, "pageShowCanvas_Map"))
        )

        # If login is successful, set the status
        status["logged_in"] = True
        status["online"] = True
        status["last_action"] = "Logged in successfully"
        status["errors"] = None

    except Exception as e:
        # Capture a screenshot if login fails
        capture_screenshot(driver, name="login_failure")
        status["logged_in"] = False
        status["online"] = False
        status["errors"] = f"Login failed: {str(e)}"
        status["last_failure_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status["last_action"] = "Login attempt failed"
        print(f"Login failed: {str(e)}")

        driver.quit()
        return None

    return driver

# Ensure the session is still valid, if not, re-login
def ensure_logged_in(driver):
    global status
    try:
        driver.find_element(By.ID, "divDevicesListInfo")  # Check if session is still valid
    except Exception:
        # Session expired, try to re-login
        print("Session expired, trying to re-login.")
        status["logged_in"] = False
        driver = perform_login()
    return driver

# Function to scrape GPS data
def scrape_gps_data(driver):
    global gps_data, status
    try:
        gps_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "divDevicesListInfo"))
        )
        gps_data = gps_element.text  # Modify this to extract structured data if needed
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
        alarm_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "divExceptionMessageDivInfo"))
        )
        alarm_data = alarm_element.text  # Modify this to extract structured data if needed
        status["scraping_attempts"] += 1
        status["last_action"] = "Alarm data scraped successfully"
        status["errors"] = None
    except Exception as e:
        status["errors"] = f"Failed to scrape Alarm data: {str(e)}"
        status["last_failure_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status["last_action"] = "Scraping Alarm data failed"

# Periodic task to update GPS and Alarm data every 10 seconds
def periodic_scraping():
    global status
    driver = perform_login()
    while True:
        if driver:
            # Ensure session is active, re-login if needed
            driver = ensure_logged_in(driver)

            if driver and status["logged_in"]:
                scrape_gps_data(driver)
                scrape_alarm_data(driver)

        # Wait for 10 seconds before the next scrape
        time.sleep(10)

# Start the periodic scraping in a separate thread
scraping_thread = Thread(target=periodic_scraping)
scraping_thread.start()

# Route to check the status
@app.get("/status")
def get_status():
    return status

# Route to get the last GPS data
@app.get("/gps")
def get_gps_data():
    if gps_data:
        return {"gps_data": gps_data}
    return {"error": "No GPS data available"}

# Route to get the last Alarm data
@app.get("/alarms")
def get_alarm_data():
    if alarm_data:
        return {"alarm_data": alarm_data}
    return {"error": "No Alarm data available"}
