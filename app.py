from fastapi import FastAPI
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time
from datetime import datetime, timedelta
import json

# Load configuration from config.json
with open("config.json", "r") as config_file:
    config = json.load(config_file)

# Extract variables from the config
login = config.get("login")
password = config.get("password")
url_login = config.get("url_login")
max_scrape_attempts = config.get("max_scrape_attempts", 3)
max_login_attempts = config.get("max_login_attempts", 3)
retry_after_hours = config.get("retry_after_hours", 6)

# Initialize FastAPI app
app = FastAPI()

# Global variables to store session info and status
session_cookies = None
api_status = {
    "logged_in": False,
    "online": False,
    "errors": None,
    "scraping_attempts": 0,
    "login_attempts": 0,
    "last_action": "",
    "last_failure_time": None
}

# Root endpoint to check if the API is running
@app.get("/")
def read_root():
    return {"message": "API is running!"}

# Function to update API status
def update_status(key, value):
    global api_status
    api_status[key] = value

# Function to reset failure counters after a given time
def reset_failure_counters():
    global api_status
    if api_status["last_failure_time"]:
        failure_time = api_status["last_failure_time"]
        if datetime.now() > failure_time + timedelta(hours=retry_after_hours):
            update_status("scraping_attempts", 0)
            update_status("login_attempts", 0)
            update_status("last_failure_time", None)
            print("Failure counters reset after timeout.")

# Function to perform login using Selenium and retrieve cookies
def perform_login():
    global session_cookies, api_status
    
    # Reset failure counters if enough time has passed
    reset_failure_counters()
    
    # Limit login attempts
    if api_status["login_attempts"] >= max_login_attempts:
        update_status("errors", "Max login attempts reached")
        update_status("last_action", "Login failed")
        print("Max login attempts reached. Login halted.")
        return None
    
    # Configure headless mode for Selenium
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")

    # Initialize Selenium WebDriver
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        # Open the login page
        driver.get(url_login)

        # Step 1: Find and click the div to switch to 'B' login type
        driver.find_element(By.ID, "changBar0").click()
        time.sleep(1)  # Wait for the switch to complete

        # Step 2: Find and fill the login form
        username_field = driver.find_element(By.NAME, "txtUserName")
        password_field = driver.find_element(By.NAME, "txtAccountPassword")

        # Enter login credentials
        username_field.send_keys(login)
        password_field.send_keys(password)
        
        # Step 3: Click the login button
        login_button = driver.find_element(By.ID, "btnLogin")
        login_button.click()

        # Wait for the page to load after clicking the login button
        time.sleep(5)

        # Check if the login was successful
        if "dashboard" in driver.current_url:
            session_cookies = driver.get_cookies()
            update_status("logged_in", True)
            update_status("online", True)
            update_status("errors", None)
            update_status("login_attempts", 0)  # Reset login attempts on success
            update_status("last_action", "Login successful")
            print("Login successful! Cookies saved.")
        else:
            update_status("logged_in", False)
            update_status("errors", "Login failed!")
            update_status("login_attempts", api_status["login_attempts"] + 1)
            print(f"Login failed! Attempts: {api_status['login_attempts']}")
            session_cookies = None
            if api_status["login_attempts"] >= max_login_attempts:
                update_status("last_failure_time", datetime.now())
    
    except Exception as e:
        update_status("online", False)
        update_status("errors", str(e))
        update_status("login_attempts", api_status["login_attempts"] + 1)
        update_status("last_action", "Login error")
        print(f"Error during login: {str(e)}")
        session_cookies = None
        if api_status["login_attempts"] >= max_login_attempts:
            update_status("last_failure_time", datetime.now())

    return driver

# Function to check if cookies are still valid
def cookies_valid(driver):
    if not session_cookies:
        return False
    return True

# Function to ensure the login is valid before scraping
def ensure_logged_in():
    driver = None
    # Perform login if not logged in or if session cookies are invalid
    if not api_status["logged_in"] or not cookies_valid(driver):
        driver = perform_login()
    return driver

# Function to extract GPS data from the table in div 'divDevicesListInfo'
def extract_gps_data(driver):
    try:
        # Locate the table inside the div with id 'divDevicesListInfo'
        table_div = driver.find_element(By.ID, "divDevicesListInfo")
        rows = table_div.find_elements(By.TAG_NAME, "tr")
        
        # List to store the GPS data
        gps_data = []
        
        # Iterate through the rows and extract cell data
        for row in rows:
            cells = row.find_elements(By.TAG_NAME, "td")
            row_data = [cell.text for cell in cells]  # Get the text from each cell
            if row_data:  # Only add non-empty rows
                gps_data.append(row_data)

        update_status("last_action", "GPS data extracted successfully")
        return gps_data

    except Exception as e:
        update_status("errors", str(e))
        update_status("last_action", "GPS data extraction failed")
        print(f"Error extracting GPS data: {str(e)}")
        return {"error": "Failed to extract GPS data"}

# Function to extract alarm data from the table in div 'divExceptionMessageDivInfo'
def extract_alarm_data(driver):
    try:
        # Locate the table inside the div with id 'divExceptionMessageDivInfo'
        table_div = driver.find_element(By.ID, "divExceptionMessageDivInfo")
        rows = table_div.find_elements(By.TAG_NAME, "tr")
        
        # List to store the alarm data
        alarm_data = []
        
        # Iterate through the rows and extract cell data
        for row in rows:
            cells = row.find_elements(By.TAG_NAME, "td")
            row_data = [cell.text for cell in cells]  # Get the text from each cell
            if row_data:  # Only add non-empty rows
                alarm_data.append({
                    "target_name": row_data[0],
                    "id_no": row_data[1],
                    "alarm_type": row_data[2],
                    "alarm_time": row_data[3],
                    "position_time": row_data[4],
                    "device_type": row_data[5],
                    "operate": row_data[6]
                })

        update_status("last_action", "Alarm data extracted successfully")
        return alarm_data

    except Exception as e:
        update_status("errors", str(e))
        update_status("last_action", "Alarm data extraction failed")
        print(f"Error extracting alarm data: {str(e)}")
        return {"error": "Failed to extract alarm data"}

# Function to check API status (online, logged in, errors)
@app.get("/status")
def get_status():
    return api_status

# Endpoint to log in and scrape GPS data
@app.get("/gps")
def scrape_gps_data():
    # Perform login check and re-login if necessary
    driver = ensure_logged_in()
    
    # Reset failure counters if enough time has passed
    reset_failure_counters()

    # Limit scraping attempts
    if api_status["scraping_attempts"] >= max_scrape_attempts:
        update_status("errors", "Max scrape attempts reached")
        update_status("last_action", "Scraping halted due to failures")
        print("Max scrape attempts reached. Scraping halted.")
        return {"error": "Max scrape attempts reached"}

    # Track scraping attempt
    update_status("scraping_attempts", api_status["scraping_attempts"] + 1)
    
    # Extract data from the GPS table
    gps_data = extract_gps_data(driver)
    
    # Close the Selenium driver
    driver.quit()

    # If scraping successful, reset attempts
    if not api_status["errors"]:
        update_status("scraping_attempts", 0)

    # Return the extracted GPS data
    return {"gps_data": gps_data}

# Endpoint to log in and scrape alarm data
@app.get("/alarms")
def scrape_alarm_data():
    # Perform login check and re-login if necessary
    driver = ensure_logged_in()

    # Reset failure counters if enough time has passed
    reset_failure_counters()

    # Limit scraping attempts
    if api_status["scraping_attempts"] >= max_scrape_attempts:
        update_status("errors", "Max scrape attempts reached")
        update_status("last_action", "Scraping halted due to failures")
        print("Max scrape attempts reached. Scraping halted.")
        return {"error": "Max scrape attempts reached"}

    # Track scraping attempt
    update_status("scraping_attempts", api_status["scraping_attempts"] + 1)
    
    # Extract data from the alarm table
    alarm_data = extract_alarm_data(driver)
    
    # Close the Selenium driver
    driver.quit()

    # If scraping successful, reset attempts
    if not api_status["errors"]:
        update_status("scraping_attempts", 0)

    # Return the extracted alarm data
    return {"alarm_data": alarm_data}
