import time
from datetime import datetime
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

# Helper function to capture a screenshot during the login process
def capture_screenshot(driver, name="screenshot"):
    screenshot_path = os.path.join(os.getcwd(), f"{name}.png")
    driver.save_screenshot(screenshot_path)
    print(f"Screenshot saved to {screenshot_path}")

# Function to handle login
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

        # Wait for successful login or error
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "divDevicesListInfo"))  # This should appear only after login
        )
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

    finally:
        driver.quit()

    return driver


# Check if the session is still logged in
def ensure_logged_in():
    global status
    if not status["logged_in"]:
        status["login_attempts"] += 1
        driver = perform_login()
        if not status["logged_in"]:
            return None  # Login failed, cannot proceed
    return driver


# Route to check status
@app.get("/status")
def get_status():
    return status


# Route to scrape GPS data (example, modify as per requirement)
@app.get("/gps")
def scrape_gps_data():
    global status
    driver = ensure_logged_in()
    if not driver:
        return {"error": "Failed to log in"}

    # Scraping logic for GPS data
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "divDevicesListInfo"))
        )
        # Continue scraping...
        status["scraping_attempts"] += 1
        status["last_action"] = "GPS data scraped successfully"
        return {"message": "GPS data scraped"}

    except Exception as e:
        status["errors"] = f"Scraping failed: {str(e)}"
        status["last_failure_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status["last_action"] = "Scraping failed"
        return {"error": "Failed to scrape GPS data"}

    finally:
        driver.quit()
