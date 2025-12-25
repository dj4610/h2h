"""
File: browser_automation.py
Update: 25 Des 2025 - Direct vote Hearts2Hearts via redirect URL (VPS friendly)
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
        self.direct_url = "https://global.prizm.co.kr/member/login?redirect_url=%2Fstory%2Fgda25%2Fvote%2F712"  # Direct H2H!

    def _setup_driver(self):
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")  # Headless untuk VPS (hemat resource)
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => false});")
        self.wait = WebDriverWait(self.driver, 50)

    def _solve_recaptcha_v2(self, sitekey, url):
        if not self.api_key:
            return False, "No 2CAPTCHA key"
        
        print("Solving reCAPTCHA v2...")
        payload = {'key': self.api_key, 'method': 'userrecaptcha', 'googlekey': sitekey, 'pageurl': url, 'json': 1}
        response = requests.post("http://2captcha.com/in.php", data=payload).json()
        if response.get('status') != 1:
            return False, response.get('request')
        
        captcha_id = response['request']
        for _ in range(40):
            time.sleep(5)
            res = requests.get(f"http://2captcha.com/res.php?key={self.api_key}&action=get&id={captcha_id}&json=1").json()
            if res.get('status') == 1:
                token = res['request']
                self.driver.execute_script(f'document.getElementById("g-recaptcha-response").innerHTML="{token}";')
                self.driver.execute_script("___grecaptcha_cfg.clients[0].callback('" + token + "');")
                return True, "Solved"
            if res.get('request') != 'CAPCHA_NOT_READY':
                return False, res.get('request')
        return False, "Timeout"

    def initiate_login_sequence(self, email):
        self._setup_driver()
        try:
            self.driver.get(self.direct_url)
            time.sleep(5)

            email_field = self.wait.until(EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Email' or @type='email']")))
            email_field.clear()
            email_field.send_keys(email)

            if self.driver.find_elements(By.CSS_SELECTOR, "[data-sitekey]"):
                sitekey = self.driver.find_element(By.CSS_SELECTOR, "[data-sitekey]").get_attribute("data-sitekey")
                success, msg = self._solve_recaptcha_v2(sitekey, self.driver.current_url)
                if not success:
                    return f"CAPTCHA failed: {msg}"

            submit_btn = self.driver.find_element(By.XPATH, "//button[@type='submit' or contains(text(), 'Next')]")
            submit_btn.click()

            self.wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='tel' or contains(@name, 'code')]")))
            return "OTP_SENT"
        except Exception as e:
            return f"Error: {str(e)}"

    # ... (submit_otp, submit_2fa_and_login, perform_voting_hearts2hearts sama seperti versi sebelumnya)

    def close_browser(self):
        if self.driver:
            self.driver.quit()
