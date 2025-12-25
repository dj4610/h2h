"""
File: browser_automation.py
Deskripsi: Modul Selenium untuk Prizm Global Voting (Update Des 2025 - GDA 2026)
"""
import time
import os
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

class PrizmVotingBot:
    def __init__(self):
        self.driver = None
        self.wait = None
        self.api_key = os.getenv("2CAPTCHA_API_KEY")
        self.target_url = "https://global.prizm.co.kr/"  # Homepage dulu, lebih stabil
        self.voting_url = "https://global.prizm.co.kr/story/gda25"  # Masih aktif untuk GDA

    def _setup_driver(self):
        chrome_options = Options()
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--disable-infobars")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        self.wait = WebDriverWait(self.driver, 30)

    def solve_captcha(self):
        try:
            print("Mendeteksi CAPTCHA...")
            current_url = self.driver.current_url

            # ReCaptcha V2
            if self.driver.find_elements(By.CSS_SELECTOR, "iframe[src*='recaptcha']"):
                print("ReCaptcha V2 terdeteksi.")
                sitekey_elem = self.driver.find_element(By.CSS_SELECTOR, "[data-sitekey]")
                sitekey = sitekey_elem.get_attribute("data-sitekey") if sitekey_elem else None
                if not sitekey:
                    return False, "Sitekey tidak ditemukan"
                # ... (sama seperti sebelumnya, kirim ke 2Captcha)

            # AWS WAF (jika ada script wafParams)
            try:
                waf_params = self.driver.execute_script("return window.wafParams || null;")
                if waf_params and waf_params.get('key'):
                    print("AWS WAF terdeteksi.")
                    # ... logic sama
            except:
                pass

            print("Tidak ada CAPTCHA atau sudah bypass.")
            return True, "No CAPTCHA or bypassed"

        except Exception as e:
            return False, f"CAPTCHA error: {str(e)}"

    # ... (_poll_2captcha_result sama seperti asli, tapi tambah check response is not None)

    def initiate_login_sequence(self, email):
        self._setup_driver()
        try:
            self.driver.get(self.target_url)
            time.sleep(3)

            # Klik Login (cari tombol login global)
            login_btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Log in') or contains(text(), 'Login')] | //a[contains(@href, 'login')]")))
            login_btn.click()

            # Input email
            email_field = self.wait.until(EC.presence_of_element_located((By.NAME, "email")))
            email_field.clear()
            email_field.send_keys(email)

            # Bypass CAPTCHA jika ada
            success, msg = self.solve_captcha()
            if not success:
                return f"CAPTCHA Gagal: {msg}"

            # Submit
            submit_btn = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']")))
            submit_btn.click()

            # Tunggu OTP page
            self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='tel'], input[name*='code']")))
            return "OTP_SENT"

        except Exception as e:
            return f"Login awal error: {str(e)}"

    # submit_otp & submit_2fa_and_login (sama, tapi tambah try-except lebih ketat & wait lebih lama)

    def perform_voting_hearts2hearts(self):
        try:
            self.driver.get(self.voting_url)
            time.sleep(5)

            # Cari candidate Hearts2Hearts (update XPath lebih fleksibel)
            hearts_xpath = "//div[contains(text(), 'Hearts2Hearts')]/following::button[contains(@class, 'vote') or contains(text(), 'Vote')]"
            vote_btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, hearts_xpath)))
            self.driver.execute_script("arguments[0].scrollIntoView(true);", vote_btn)
            vote_btn.click()

            # Handle ad atau confirm
            time.sleep(3)
            try:
                confirm = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Confirm') or contains(text(), 'OK')]")), timeout=5)
                confirm.click()
            except:
                pass

            time.sleep(5)
            screenshot_path = f"proof_{int(time.time())}.png"
            self.driver.save_screenshot(screenshot_path)

            return {"status": True, "timestamp": time.ctime(), "screenshot": screenshot_path, "message": "Vote sukses untuk Hearts2Hearts!"}

        except Exception as e:
            return {"status": False, "message": f"Voting error: {str(e)}"}

    def close_browser(self):
        if self.driver:
            self.driver.quit()
