import json
import time
from fastapi import FastAPI
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from pydantic import BaseModel

app = FastAPI()

# Load the configuration file
with open('config.json', 'r') as f:
    config = json.load(f)

# Global status dictionary for the /status route
status = {
    "logged_in": False,
    "online": False,
    "errors": None,
    "scraping_attempts": 0,
    "login_attempts": 0,
    "last_action": "",
    "last_failure_time": None
}

# Helper function to update status and print logs
def update_status(key, value, action_desc=None):
    status[key] = value
    if action_desc:
        print(f"[DEBUG] {action_desc}: {value}")

# Function to perform login
def login(driver):
    try:
        # Attempt to switch login type
        print("[DEBUG] Attempting to switch login type")
        login_type_element = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "changBar0"))
        )
        login_type_element.click()
        update_status("last_action", "Login type switched")

        # Fill in login form
        print("[DEBUG] Filling in login credentials")
        driver.find_element(By.ID, "txtUserName").send_keys(config['login'])
        driver.find_element(By.ID, "txtAccountPassword").send_keys(config['password'])

        # Click login button
        print("[DEBUG] Clicking login button")
        login_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "btnLogin"))
        )
        login_button.click()

        # Check if login was successful
        time.sleep(5)  # Allow time for login
        if "dashboard" in driver.current_url:
            update_status("logged_in", True, "Successfully logged in")
            print("[DEBUG] Login successful")
        else:
            raise Exception("Login failed: Incorrect credentials or unexpected login flow")

    except TimeoutException as e:
        update_status("errors", f"Timeout while attempting to login: {str(e)}")
        update_status("last_failure_time", time.strftime("%Y-%m-%d %H:%M:%S"))
        raise Exception(f"Timeout during login process: {str(e)}")

    except Exception as e:
        update_status("errors", f"Login error: {str(e)}")
        update_status("last_failure_time", time.strftime("%Y-%m-%d %H:%M:%S"))
        print(f"[ERROR] {str(e)}")
        raise e

# Function to scrape data from the page
def scrape_data(driver):
    try:
        print("[DEBUG] Attempting to scrape GPS data")
        gps_table = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "divDevicesListInfo"))
        )
        gps_data = gps_table.text  # You can parse it further
        update_status("scraping_attempts", status['scraping_attempts'] + 1)
        update_status("last_action", "Scraping GPS data")

        print("[DEBUG] Attempting to scrape Alarm data")
        alarm_table = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "divExceptionMessageDivInfo"))
        )
        alarm_data = alarm_table.text  # You can parse it further
        update_status("last_action", "Scraping Alarm data")
        
        # Returning sample structured data
        return {
            "gps_data": gps_data,
            "alarm_data": alarm_data
        }

    except TimeoutException as e:
        update_status("errors", f"Timeout while attempting to scrape data: {str(e)}")
        update_status("last_failure_time", time.strftime("%Y-%m-%d %H:%M:%S"))
        raise Exception(f"Timeout during scraping process: {str(e)}")

    except Exception as e:
        update_status("errors", f"Scraping error: {str(e)}")
        update_status("last_failure_time", time.strftime("%Y-%m-%d %H:%M:%S"))
        print(f"[ERROR] {str(e)}")
        raise e

# FastAPI route to check the system status
@app.get("/status")
def get_status():
    return status

# FastAPI route to trigger scraping and login process
@app.get("/gps")
def get_gps_data():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

    driver = webdriver.Chrome(options=options)
    driver.get(config['url_login'])

    # Login and scrape data
    try:
        update_status("login_attempts", status['login_attempts'] + 1)
        login(driver)

        # After successful login, scrape data
        data = scrape_data(driver)

        # Mark system as online and logged in
        update_status("online", True)
        return data

    except Exception as e:
        update_status("errors", str(e))
        return {"error": str(e)}

    finally:
        driver.quit()

# Reset failures after a certain amount of hours
@app.get("/reset")
def reset_failures():
    status['scraping_attempts'] = 0
    status['login_attempts'] = 0
    update_status("errors", None)
    update_status("last_failure_time", None)
    update_status("last_action", "Reset performed")
    print("[DEBUG] Resetting failure counters")
    return {"message": "Failure counters reset"}
