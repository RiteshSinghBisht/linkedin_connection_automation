# 🤖 LinkedIn Connection Automation Bot (GUI + Turbo Mode)

An advanced Python automation tool built with **Selenium** and **Tkinter** to automate LinkedIn connection requests. 

It features a smart "Commercial Use Limit" bypass that automatically switches from Search mode to "My Network" mode, ensuring daily targets are met even when LinkedIn restricts profile searches.

## 🚀 Features

* **GUI Interface:** User-friendly dashboard built with Tkinter.
* **Smart Limit Bypass:** Detects LinkedIn's "Commercial Use Limit" and auto-switches strategy.
* **Turbo Mode:** Rapidly processes connections in "My Network" mode (up to 50/min).
* **Autofill Credentials:** Securely saves your login details and settings locally.
* **Search & Connect:** Sends requests based on specific keywords (e.g., "Recruiter", "HR").
* **Personalized Notes:** Option to attach custom notes to connection requests.
* **Safety Delays:** Randomized delays to mimic human behavior (in Standard Mode).

## 🛠️ Installation

1.  **Clone the repository**
    ```bash
    git clone [https://github.com/YOUR_USERNAME/linkedin-automation-bot.git](https://github.com/YOUR_USERNAME/linkedin-automation-bot.git)
    cd linkedin-automation-bot
    ```

2.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Run the Application**
    ```bash
    python linkedin_bot_v9.py
    ```

## 📦 How to Build (.exe / .app)

To convert this script into a standalone executable:

```bash
pip install pyinstaller
pyinstaller --noconfirm --onefile --windowed --name "LinkedInBot" --clean linkedin_bot_v9.py