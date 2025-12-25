"""
File: browser_automation.py
Deskripsi: Modul Selenium untuk interaksi browser Prizm Global & Bypass CAPTCHA
"""
import time
import os
import requests
import pickle
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
        # URL Entry Point Login
        self.target_url = "https://global.prizm.co.kr/mypage/setting"
        # URL Event Voting (Sesuaikan dengan event aktif, misal Golden Disc 2025)
        self.voting_url = "https://global.prizm.co.kr/story/gda25" 

    def _setup_driver(self):
        """Konfigurasi Driver dengan parameter Anti-Deteksi (Stealth)"""
        chrome_options = Options()
        # Non-aktifkan flag 'navigator.webdriver' agar tidak terdeteksi sebagai bot
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--start-maximized")
        # User-Agent manusiawi
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36")
        
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        self.wait = WebDriverWait(self.driver, 25) # Timeout 25 detik

    def solve_captcha(self):
        """
        Logika pemecahan CAPTCHA (Support ReCaptcha V2 & AWS WAF)
        """
        try:
            print(" Mendeteksi tipe CAPTCHA...")
            current_url = self.driver.current_url
            
            # Cek 1: Google ReCaptcha V2
            recaptcha_frames = self.driver.find_elements(By.XPATH, "//iframe[contains(@src, 'recaptcha')]")
            if recaptcha_frames:
                print(" ReCaptcha V2 Terdeteksi.")
                sitekey_elem = self.driver.find_element(By.CSS_SELECTOR, "[data-sitekey]")
                sitekey = sitekey_elem.get_attribute("data-sitekey")
                
                # Kirim request ke 2Captcha
                req_url = "http://2captcha.com/in.php"
                payload = {
                    'key': self.api_key, 'method': 'userrecaptcha',
                    'googlekey': sitekey, 'pageurl': current_url, 'json': 1
                }
                response = requests.post(req_url, data=payload).json()
                if response['status']!= 1: return False, f"2Captcha Error: {response.get('request')}"
                return self._poll_2captcha_result(response['request'], is_aws=False)

            # Cek 2: AWS WAF Captcha
            waf_params = self.driver.execute_script("return window.wafParams;")
            if waf_params:
                print(" AWS WAF Terdeteksi.")
                req_url = "http://2captcha.com/in.php"
                payload = {
                    'key': self.api_key, 'method': 'amazon_waf',
                    'sitekey': waf_params.get('key'), 'iv': waf_params.get('iv'),
                    'context': waf_params.get('context'), 'pageurl': current_url, 'json': 1
                }
                response = requests.post(req_url, data=payload).json()
                if response['status']!= 1: return False, f"2Captcha AWS Error: {response.get('request')}"
                return self._poll_2captcha_result(response['request'], is_aws=True)

            print(" Tidak ada CAPTCHA yang dikenali. Lanjut.")
            return True, "No Captcha"

        except Exception as e:
            return False, str(e)

    def _poll_2captcha_result(self, request_id, is_aws=False):
        """Menunggu worker 2Captcha menyelesaikan tugas"""
        print(f" Menunggu solusi CAPTCHA (ID: {request_id})...")
        for _ in range(20): # Timeout ~100 detik
            time.sleep(5)
            res = requests.get(f"http://2captcha.com/res.php?key={self.api_key}&action=get&id={request_id}&json=1").json()
            if res['status'] == 1:
                token = res['request']
                if is_aws:
                    cookie = {'name': 'aws-waf-token', 'value': token, 'domain': '.prizm.co.kr'}
                    self.driver.add_cookie(cookie)
                    self.driver.refresh()
                else:
                    self.driver.execute_script(f'document.getElementById("g-recaptcha-response").innerHTML="{token}";')
                return True, "Solved"
            if res['request'] == 'ERROR_CAPTCHA_UNSOLVABLE': return False, "Unsolvable"
        return False, "Timeout"

    def initiate_login_sequence(self, email):
        self._setup_driver()
        try:
            print(f" Membuka Prizm untuk email: {email}")
            self.driver.get(self.target_url)
            
            # Klik Login (Selector dinamis untuk antisipasi perubahan UI)
            login_btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//*")))
            login_btn.click()
            
            # Input Email
            email_field = self.wait.until(EC.visibility_of_element_located((By.NAME, "email")))
            email_field.clear()
            email_field.send_keys(email)
            
            # Solve Captcha sebelum submit email
            success, msg = self.solve_captcha()
            if not success: return f"Captcha Fail: {msg}"
            
            # Submit Email
            submit_btn = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            submit_btn.click()
            
            # Validasi berhasil masuk page OTP
            self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[name*='code'], input[type='tel']")))
            return "OTP_SENT"
        except Exception as e:
            return str(e)

    def submit_otp(self, otp_code):
        try:
            print(f" Input OTP: {otp_code}")
            otp_input = self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input[name*='code'], input[type='tel']")))
            otp_input.send_keys(otp_code)
            
            # Klik Verify/Next
            verify_btn = self.driver.find_element(By.XPATH, "//*[contains(text(), 'Verify') or contains(text(), 'Next')]")
            verify_btn.click()
            
            # Cek apakah masuk ke halaman 2FA (Authenticator)
            self.wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Authenticator') or contains(@name, '2fa')]")))
            return "2FA_REQUIRED"
        except Exception as e:
            return str(e)

    def submit_2fa_and_login(self, code_2fa):
        try:
            print(f" Input 2FA: {code_2fa}")
            input_2fa = self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input[type='tel'], input[name*='otp']")))
            input_2fa.send_keys(code_2fa)
            
            confirm_btn = self.driver.find_element(By.XPATH, "//*[contains(text(), 'Confirm') or contains(text(), 'Log in')]")
            confirm_btn.click()
            
            # Verifikasi Login Sukses (Cari elemen profil/mypage)
            self.wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(@href, '/mypage')]")))
            return True
        except Exception as e:
            print(f"Login Error: {e}")
            return False

    def perform_voting_hearts2hearts(self):
        try:
            print(" Menuju halaman voting Hearts2Hearts...")
            self.driver.get(self.voting_url)
            
            # Strategi Voting Spesifik Hearts2Hearts
            # Mencari teks 'Hearts2Hearts' dan klik tombol di dekatnya
            hearts_xpath = "//div[contains(@class, 'candidate')]//div[contains(text(), 'Hearts2Hearts')]/ancestor::div[contains(@class, 'candidate')]//button"
            
            vote_btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, hearts_xpath)))
            self.driver.execute_script("arguments.scrollIntoView({block: 'center'});", vote_btn)
            time.sleep(1)
            vote_btn.click()
            
            # Handle Popup Konfirmasi
            try:
                confirm_popup = WebDriverWait(self.driver, 3).until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Confirm') or contains(text(), 'Ok')]")))
                confirm_popup.click()
            except: pass
            
            time.sleep(3) # Tunggu animasi selesai
            
            # Bukti Screenshot
            screenshot_path = f"vote_proof_{int(time.time())}.png"
            self.driver.save_screenshot(screenshot_path)
            
            return {"status": True, "timestamp": time.ctime(), "screenshot": screenshot_path}
            
        except Exception as e:
            return {"status": False, "message": str(e)}

    def close_browser(self):
        if self.driver: self.driver.quit()
