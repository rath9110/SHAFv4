This project is done as a template that can be customized to fit a certain segment e.g. clothes, consumer electronics or furniture

Next step:
Option A (recommended): Selenium Manager (built into Selenium ≥ 4.6)

What you change

Do not install chromium-driver in the image.

Use webdriver.Chrome(options=...) without passing a Service(executable_path=...).

Keep options.binary_location = "/usr/bin/chromium" so Selenium can detect the browser version.

Dockerfile

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Install Chromium only (no chromedriver)
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium \
    fonts-liberation fonts-dejavu-core fonts-noto-color-emoji \
    ca-certificates curl unzip \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .
ENV PORT=8000
EXPOSE 8000
CMD ["uvicorn","main:app","--host","0.0.0.0","--port","8000"]


requirements.txt

fastapi
uvicorn[standard]
requests
selenium>=4.14.0
beautifulsoup4
zeep
lxml


Python driver setup

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

def get_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1280,800")
    options.add_argument("--disable-blink-features=AutomationControlled")

    # Tell Selenium we use Chromium, not Chrome from /Applications etc.
    options.binary_location = "/usr/bin/chromium"

    # IMPORTANT: Do NOT pass Service(executable_path=...)
    # Selenium Manager will auto-download the correct chromedriver for Chromium 142
    driver = webdriver.Chrome(options=options)
    return driver


Selenium Manager will detect the Chromium version by invoking it, download the matching driver, cache it, and use it.