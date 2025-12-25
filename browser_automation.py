"""
File: browser_automation.py
Update: 25 Des 2025 - Direct login + vote Hearts2Hearts (ID 712)
"""
import time
import os
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

class PrizmVotingBot:
    def __init__(self):
        self.driver = None
        self.wait = None
        self.api_key = os.getenv("2CAPTCHA_API_KEY")
        self.direct_vote_url = "https://global.prizm.co.kr/member/login?redirect_url=%2Fstory%2Fgda25%2Fvote%2F712"  # Direct H2H!

    def _setup_driver(self):
        chrome_options = Options()
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")  # Penting untuk Codespaces!
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => false});")
        self.wait = WebDriverWait(self.driver, 40)

    def _solve_recaptcha_v2(self, sitekey, url):
        # Logic sama seperti sebelumnya, tapi tambah trigger callback lebih kuat
        # (copy dari versi lama kamu, tambah checkbox click jika perlu)
        # ... (paste logic _solve_recaptcha_v2 lengkap)
        pass  # Ganti dengan kode solve lengkap dari versi lama

    def initiate_login_sequence(self, email):
        self._setup_driver()
        try:
            self.driver.get(self.direct_vote_url)
            time.sleep(4)

            # Email field langsung ada
            email_field = self.wait.until(EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Email' or @type='email' or contains(@name, 'email')]")))
            email_field.clear()
            email_field.send_keys(email)

            # Solve reCAPTCHA jika muncul
            if self.driver.find_elements(By.XPATH, "//iframe[contains(@title, 'reCAPTCHA')]"):
                sitekey_elem = self.driver.find_element(By.CSS_SELECTOR, "[data-sitekey]")
                sitekey = sitekey_elem.get_attribute("data-sitekey")
                success, msg = self._solve_recaptcha_v2(sitekey, self.driver.current_url)
                if not success:
                    return f"CAPTCHA gagal: {msg}"

            # Submit
            submit_btn = self.driver.find_element(By.XPATH, "//button[@type='submit' or contains(text(), 'Next')]")
            submit_btn.click()

            # Tunggu OTP field
            self.wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='tel' or contains(@placeholder, 'code')]")))
            return "OTP_SENT"

        except Exception as e:
            return f"Error direct login: {str(e)}"

    # submit_otp, submit_2fa_and_login, perform_voting_hearts2hearts
    # Sama seperti versi sebelumnya, tapi di perform_voting: handle ad video + klik Confirm final

    def close_browser(self):
        if self.driver:
            self.driver.quit()
