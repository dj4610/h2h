"""
File: browser_automation.py
Update: Des 2025 - Playwright untuk Prizm GDA Voting (Hearts2Hearts)
"""
import time
import os
import requests
import asyncio
from playwright.async_api import async_playwright

class PrizmVotingBot:
    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
        self.api_key = os.getenv("2CAPTCHA_API_KEY")
        self.voting_url = "https://global.prizm.co.kr/story/gda25"

    async def _solve_recaptcha_v2(self, sitekey, page_url):
        if not self.api_key:
            return False, "No 2CAPTCHA key"
        
        payload = {'key': self.api_key, 'method': 'userrecaptcha', 'googlekey': sitekey, 'pageurl': page_url, 'json': 1}
        response = requests.post("http://2captcha.com/in.php", data=payload).json()
        if response.get('status') != 1:
            return False, response.get('request')
        
        captcha_id = response['request']
        for _ in range(40):
            time.sleep(5)
            res = requests.get(f"http://2captcha.com/res.php?key={self.api_key}&action=get&id={captcha_id}&json':1").json()
            if res.get('status') == 1:
                token = res['request']
                await self.page.evaluate(f'''() => {{
                    document.getElementById("g-recaptcha-response").innerHTML = "{token}";
                    if (typeof ___grecaptcha_cfg !== 'undefined') {{
                        ___grecaptcha_cfg.clients[0].callback("{token}");
                    }}
                }}''')
                return True, "Solved"
            if res.get('request') != 'CAPCHA_NOT_READY':
                return False, res.get('request')
        return False, "Timeout"

    async def initiate_login_sequence(self, email):
        async with async_playwright() as p:
            self.browser = await p.chromium.launch(headless=False)  # False untuk debug, nanti True
            self.context = await self.browser.new_context(viewport={"width": 1920, "height": 1080})
            self.page = await self.context.new_page()
            await self.page.goto(self.voting_url, wait_until="networkidle")
            
            try:
                # Klik Vote Hearts2Hearts (selector robust)
                await self.page.wait_for_selector("text=/Hearts2Hearts/i", timeout=30000)
                vote_btn = await self.page.query_selector("//div[contains(text(), 'Hearts2Hearts')]//following::button[contains(text(), 'Vote')]")
                await vote_btn.scroll_into_view_if_needed()
                await vote_btn.click()
                
                # Tunggu modal login
                await self.page.wait_for_selector("input[placeholder='Email']", timeout=20000)
                await self.page.fill("input[placeholder='Email']", email)
                
                # Solve reCAPTCHA jika ada
                if await self.page.query_selector("iframe[title*='reCAPTCHA']"):
                    sitekey = await self.page.eval_on_selector("[data-sitekey]", "el => el.dataset.sitekey")
                    success, msg = await self._solve_recaptcha_v2(sitekey, self.page.url)
                    if not success:
                        await self.close_browser()
                        return f"CAPTCHA gagal: {msg}"
                
                # Submit
                await self.page.click("button:has-text('Next')")
                await self.page.wait_for_selector("input[type='tel']", timeout=20000)  # OTP field
                
                return "OTP_SENT"
            
            except Exception as e:
                await self.close_browser()
                return f"Error: {str(e)}"

    async def close_browser(self):
        if self.browser:
            await self.browser.close()
