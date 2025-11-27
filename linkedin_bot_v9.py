"""
LinkedIn Bot v1.0 - Turbo Mode & Autofill
Date: November 27, 2025
Description: 
1. Auto-switches to 'My Network' on limit.
2. My Network mode runs at high speed (Turbo).
3. Saves/Loads credentials and settings automatically.
"""

# --- UI IMPORTS ---
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import queue
import traceback

# --- BOT IMPORTS ---
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager
import time
import random
import logging
from datetime import datetime
import json
import os
import pickle

# ======================================================================
#
# SECTION 1: BOT CONFIG & LOGIC
#
# ======================================================================

# ==================== CONFIG ====================
class Config:
    EMAIL = ""
    PASSWORD = ""
    SEARCH_QUERIES = []
    MAX_CONNECTIONS_PER_DAY = 100 
    MIN_DELAY = 2
    MAX_DELAY = 4
    MAX_RUNTIME_MINUTES = 30
    USE_NOTE = False
    NOTE_TEMPLATES = [
        "Hi {name}, I'd love to connect and expand my professional network!",
        "Hello {name}, I came across your profile and would appreciate connecting.",
    ]
    
    # --- PATH MODIFICATION FOR APP/EXE ---
    # This creates a folder named "LinkedInBotData" in the user's home directory
    USER_HOME = os.path.expanduser("~")
    DATA_DIR = os.path.join(USER_HOME, "LinkedInBotData")
    
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

    LOG_FILE = os.path.join(DATA_DIR, "linkedin_bot.log")
    STATS_FILE = os.path.join(DATA_DIR, "linkedin_stats.json")
    COOKIES_FILE = os.path.join(DATA_DIR, "linkedin_cookies.pkl")
    SETTINGS_FILE = os.path.join(DATA_DIR, "linkedin_settings.json")
    
    SHOW_BROWSER = True

# ==================== LOGGING ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler(Config.LOG_FILE)]
)
logger = logging.getLogger(__name__)

class UiLogHandler(logging.Handler):
    def __init__(self, callback):
        super().__init__()
        self.callback = callback
    def emit(self, record):
        self.callback(self.format(record))

# ==================== UTILS ====================
def delay():
    time.sleep(random.uniform(Config.MIN_DELAY, Config.MAX_DELAY))

def load_stats():
    if os.path.exists(Config.STATS_FILE):
        try:
            with open(Config.STATS_FILE, 'r') as f: return json.load(f)
        except: pass
    return {'total_sent': 0, 'last_run_date': None, 'daily_count': 0, 'weekly_count': 0, 'week_start_date': None, 'sessions': []}

def save_stats(stats):
    with open(Config.STATS_FILE, 'w') as f: json.dump(stats, f, indent=4)

def check_limits(stats):
    today = datetime.now().strftime('%Y-%m-%d')
    if stats['last_run_date'] != today:
        stats['daily_count'] = 0
        stats['last_run_date'] = today
    
    week_start = stats.get('week_start_date')
    if not week_start:
        stats['week_start_date'] = today
        stats['weekly_count'] = 0
    else:
        try:
            days = (datetime.now() - datetime.strptime(week_start, '%Y-%m-%d')).days
            if days >= 7:
                stats['week_start_date'] = today
                stats['weekly_count'] = 0
        except: pass
    
    return stats['daily_count'] < Config.MAX_CONNECTIONS_PER_DAY

def show_summary(stats, session):
    logger.info("\n" + "="*70)
    logger.info("🤖 SESSION COMPLETE")
    logger.info("="*70)
    logger.info(f"   • Sent: {session['connections_sent']}")
    logger.info(f"   • Duration: {session['duration']} min")
    logger.info(f"   • Total Today: {stats['daily_count']} / {Config.MAX_CONNECTIONS_PER_DAY}")
    logger.info("="*70)

# ==================== BROWSER ====================
def setup_browser():
    opts = Options()
    opts.add_argument('--disable-blink-features=AutomationControlled')
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option('useAutomationExtension', False)
    opts.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    opts.add_argument('--disable-notifications')
    
    if not Config.SHOW_BROWSER: opts.add_argument('--headless=new')
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opts)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver

# ==================== BOT CLASS ====================

class LinkedInBot:
    def __init__(self):
        self.driver = setup_browser()
        self.wait = WebDriverWait(self.driver, 10)
        self.stats = load_stats()
        self.start = datetime.now()
        self.weekly_limit = False
        self.search_limit_reached = False
        self.page = 1
        self.query = random.choice(Config.SEARCH_QUERIES) if Config.SEARCH_QUERIES else "Ey"
        logger.info(f"🎯 Search Target: {self.query}")
    
    def save_cookies(self):
        try:
            with open(Config.COOKIES_FILE, 'wb') as f: pickle.dump(self.driver.get_cookies(), f)
            logger.info("💾 Cookies saved")
        except: pass
    
    def load_cookies(self):
        try:
            if os.path.exists(Config.COOKIES_FILE):
                self.driver.get("https://www.linkedin.com")
                time.sleep(2)
                with open(Config.COOKIES_FILE, 'rb') as f:
                    for c in pickle.load(f): self.driver.add_cookie(c)
                logger.info("🔄 Cookies loaded")
                return True
            return False
        except: return False
    
    def check_limit_popup(self):
        """Checks for weekly or commercial limits"""
        try:
            src = self.driver.page_source.lower()
            if any(p in src for p in ['weekly limit', 'try again next week']):
                logger.error("🚨 WEEKLY LIMIT DETECTED!")
                self.weekly_limit = True
                return True
            
            limit_phrases = ["reached the monthly limit", "upgrade to premium", "commercial use limit"]
            if any(p in src for p in limit_phrases):
                logger.warning("⚠️ SEARCH LIMIT REACHED!")
                self.search_limit_reached = True
                return True
            return False
        except: return False

    def login(self):
        if self.load_cookies():
            self.driver.get("https://www.linkedin.com/feed")
            time.sleep(3)
            if "feed" in self.driver.current_url:
                logger.info("✅ Session valid!")
                return True
        
        logger.info("🔐 Logging in...")
        self.driver.get("https://www.linkedin.com/login")
        time.sleep(2)
        
        try:
            self.driver.find_element(By.ID, "username").send_keys(Config.EMAIL)
            self.driver.find_element(By.ID, "password").send_keys(Config.PASSWORD)
            self.driver.find_element(By.XPATH, "//button[@type='submit']").click()
            
            time.sleep(5)
            if "captcha" in self.driver.page_source.lower():
                logger.warning("🤖 CAPTCHA! Please solve it in browser (60s timeout)...")
                WebDriverWait(self.driver, 60).until(EC.url_contains("feed"))
            
            self.save_cookies()
            return True
        except Exception as e:
            logger.error(f"❌ Login failed: {e}")
            return False

    def search(self):
        try:
            logger.info(f"🔍 Searching: {self.query}")
            box = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".search-global-typeahead__input")))
            box.click()
            box.send_keys(self.query)
            box.send_keys(Keys.RETURN)
            time.sleep(3)
            self.wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'People')]"))).click()
            time.sleep(3)
            return True
        except: return False

    # ================= TURBO MODE LOGIC =================
    def switch_to_network_mode(self):
        logger.info("\n🚀 ACTIVATING TURBO MODE: My Network Fallback")
        
        self.driver.get("https://www.linkedin.com/mynetwork/")
        time.sleep(4)
        
        count = self.stats['daily_count']
        
        while count < Config.MAX_CONNECTIONS_PER_DAY:
            # Safety check
            if (datetime.now() - self.start).seconds / 60 > Config.MAX_RUNTIME_MINUTES: break
            
            # 1. Scroll slightly to trigger lazy load
            self.driver.execute_script("window.scrollBy(0, 400);")
            time.sleep(0.5) 

            # 2. Get Buttons (Refresh list often to avoid stale elements)
            buttons = self.driver.find_elements(By.XPATH, "//button[.//span[text()='Connect']]")
            
            if not buttons:
                logger.warning("⚠️ No buttons visible, scrolling...")
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                continue

            # 3. FAST CLICK LOOP
            for btn in buttons:
                if count >= Config.MAX_CONNECTIONS_PER_DAY: break
                
                try:
                    # Turbo: Scroll and Click immediately
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                    
                    try: btn.click()
                    except: self.driver.execute_script("arguments[0].click();", btn)
                    
                    count += 1
                    logger.info(f"⚡ Turbo Sent: #{count}")
                    
                    # Minimal wait for 50/min speed (approx 1.2s total cycle)
                    # No notes, no modal checks (usually MyNetwork doesn't have modals)
                    time.sleep(0.8) 
                    
                    # Occasional save to not slow down every iteration
                    if count % 5 == 0:
                        self.stats['daily_count'] = count
                        self.stats['total_sent'] += 5
                        save_stats(self.stats)

                except Exception as e:
                    # If stale, break inner loop to re-fetch buttons
                    break 
        
        self.stats['daily_count'] = count
        save_stats(self.stats)
        return count

    def send_connections(self):
        count = self.stats['daily_count']
        
        while count < Config.MAX_CONNECTIONS_PER_DAY:
            if (datetime.now() - self.start).seconds / 60 > Config.MAX_RUNTIME_MINUTES: break
            if not check_limits(self.stats): break
            
            if self.check_limit_popup() or self.search_limit_reached:
                count = self.switch_to_network_mode()
                break

            # Regular Search Mode
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
            self.driver.execute_script("window.scrollTo(0, 0);")
            
            buttons = self.driver.find_elements(By.XPATH, "//button[span[text()='Connect']]")
            if not buttons:
                # If no buttons in search, try next page or switch
                try:
                    self.driver.find_element(By.XPATH, f"//button[@aria-label='Page {self.page+1}']").click()
                    self.page += 1
                    time.sleep(3)
                    continue
                except:
                    # End of pages or limited, switch to network
                    count = self.switch_to_network_mode()
                    break

            for btn in buttons:
                if count >= Config.MAX_CONNECTIONS_PER_DAY: break
                if self.check_limit_popup(): break

                try:
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                    time.sleep(0.5)
                    btn.click()
                    time.sleep(1)

                    # Handle Modal (Regular Mode is slower/safer)
                    try:
                        self.driver.find_element(By.XPATH, "//button[contains(., 'Send without a note')]").click()
                    except: pass # Might be auto-sent or note button not found
                    
                    # Close modal if still open (sometimes happens)
                    ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()

                    count += 1
                    self.stats['daily_count'] = count
                    self.stats['total_sent'] += 1
                    save_stats(self.stats)
                    logger.info(f"✅ #{count} Sent (Search Mode)")
                    delay() # Regular delay

                except: continue
        
        return count

    def run(self):
        if not self.login(): return
        if not self.search(): return
        self.send_connections()
        self.driver.quit()

# ======================================================================
#
# SECTION 2: UI LOGIC
#
# ======================================================================

class BotUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("LinkedIn Bot v9.0 - Turbo & Autofill")
        self.geometry("600x680")
        self.resizable(False, False)
        self.style = ttk.Style(self)
        self.style.theme_use('clam')
        
        main = ttk.Frame(self, padding="20")
        main.pack(fill="both", expand=True)
        
        ttk.Label(main, text="LinkedIn Automation", font=("Helvetica", 18, "bold")).pack(pady=(0, 15))
        
        # 1. Credentials
        creds = ttk.Labelframe(main, text="1. Credentials (Autofill Enabled)", padding="10")
        creds.pack(fill="x", pady=5)
        
        ttk.Label(creds, text="Email:").grid(row=0, column=0, sticky="w")
        self.email_ent = ttk.Entry(creds, width=40)
        self.email_ent.grid(row=0, column=1, padx=5, pady=2)
        
        ttk.Label(creds, text="Password:").grid(row=1, column=0, sticky="w")
        self.pass_ent = ttk.Entry(creds, show="*", width=40)
        self.pass_ent.grid(row=1, column=1, padx=5, pady=2)
        
        # 2. Settings
        sets = ttk.Labelframe(main, text="2. Settings", padding="10")
        sets.pack(fill="x", pady=10)
        
        # Max Connections Input
        ttk.Label(sets, text="Max Connections (Today):").grid(row=0, column=0, sticky="w")
        self.limit_var = tk.StringVar(value="100")
        self.limit_spin = ttk.Spinbox(sets, from_=1, to=200, textvariable=self.limit_var, width=10)
        self.limit_spin.grid(row=0, column=1, sticky="w", padx=5)
        ttk.Label(sets, text="(Max 200 Connection)").grid(row=0, column=2, sticky="w")

        ttk.Label(sets, text="Search Criteria:").grid(row=1, column=0, sticky="nw", pady=5)
        self.search_txt = scrolledtext.ScrolledText(sets, height=3, width=40, font=("Helvetica", 10))
        self.search_txt.grid(row=1, column=1, columnspan=2, pady=5)
        
        self.note_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(sets, text="Add Note (Search Mode Only)", variable=self.note_var).grid(row=2, column=1, sticky="w")
        
        # 3. Start
        self.btn = ttk.Button(main, text="Start Bot", command=self.start_thread)
        self.btn.pack(fill="x", pady=5)
        
        # 4. Logs
        self.log_txt = scrolledtext.ScrolledText(main, height=12, state="disabled", font=("Courier", 9))
        self.log_txt.pack(fill="both", expand=True)
        self.log_q = queue.Queue()
        
        # Load saved settings
        self.load_settings()
        self.after(100, self.update_logs)

    def load_settings(self):
        """Loads email, password, and limit from JSON"""
        if os.path.exists(Config.SETTINGS_FILE):
            try:
                with open(Config.SETTINGS_FILE, 'r') as f:
                    data = json.load(f)
                    self.email_ent.insert(0, data.get("email", ""))
                    self.pass_ent.insert(0, data.get("password", ""))
                    self.limit_var.set(data.get("limit", "100"))
                    queries = data.get("queries", [])
                    if queries:
                        self.search_txt.insert(tk.END, "\n".join(queries))
                    else:
                        self.search_txt.insert(tk.END, "Recruiter")
            except: pass
    
    def save_settings(self, email, password, limit, queries):
        """Saves settings to JSON for next time"""
        data = {
            "email": email,
            "password": password,
            "limit": limit,
            "queries": queries
        }
        try:
            with open(Config.SETTINGS_FILE, 'w') as f:
                json.dump(data, f)
        except: pass

    def start_thread(self):
        email = self.email_ent.get()
        pwd = self.pass_ent.get()
        try:
            limit = int(self.limit_var.get())
            if limit > 200: limit = 200 # Enforce hard limit
        except: limit = 100
        
        queries = [q for q in self.search_txt.get('1.0', tk.END).strip().splitlines() if q.strip()]
        
        if not email or not pwd:
            messagebox.showerror("Error", "Email & Password required")
            return
            
        # Save for next time
        self.save_settings(email, pwd, limit, queries)
        
        self.btn.config(state="disabled", text="Running...")
        self.log_txt.config(state="normal")
        self.log_txt.delete('1.0', tk.END)
        self.log_txt.config(state="disabled")
        
        threading.Thread(target=self.run_bot, args=(email, pwd, queries, limit, self.note_var.get()), daemon=True).start()

    def run_bot(self, email, pwd, queries, limit, note):
        try:
            Config.EMAIL = email
            Config.PASSWORD = pwd
            Config.SEARCH_QUERIES = queries
            Config.MAX_CONNECTIONS_PER_DAY = limit
            Config.USE_NOTE = note
            
            # Setup Log Handler
            for h in logger.handlers[:]: 
                if isinstance(h, UiLogHandler): logger.removeHandler(h)
            logger.addHandler(UiLogHandler(self.log_q.put))
            logger.setLevel(logging.INFO)
            
            bot = LinkedInBot()
            bot.run()
        except Exception as e:
            logger.error(f"Error: {e}")
        finally:
            self.after(0, lambda: self.btn.config(state="normal", text="Start Bot"))

    def update_logs(self):
        while not self.log_q.empty():
            msg = self.log_q.get()
            self.log_txt.config(state="normal")
            self.log_txt.insert(tk.END, msg + "\n")
            self.log_txt.config(state="disabled")
            self.log_txt.see(tk.END)
        self.after(100, self.update_logs)

if __name__ == "__main__":
    app = BotUI()
    app.mainloop()