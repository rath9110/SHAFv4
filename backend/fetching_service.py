from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import logging
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time
import random
from bs4 import BeautifulSoup
from zeep import Client, xsd
import shutil
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

TRADERA_API_URL = os.environ.get("TRADERA_API_URL")
TRADERA_APP_ID = os.environ.get("TRADERA_APP_ID")
TRADERA_APP_KEY = os.environ.get("TRADERA_APP_KEY")

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Log startup configuration (without exposing sensitive data)
logging.info(f"[Backend] ==================== STARTING APPLICATION ====================")
logging.info(f"[Backend] Python version: {os.sys.version}")
logging.info(f"[Backend] PORT environment variable: {os.environ.get('PORT', 'NOT SET')}")
logging.info(f"[Backend] Tradera API URL configured: {bool(TRADERA_API_URL)}")
logging.info(f"[Backend] Tradera credentials configured: {bool(TRADERA_APP_ID and TRADERA_APP_KEY)}")

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    """Log when the app is ready to accept connections."""
    logging.info(f"[Backend] ==================== APP READY ====================")
    logging.info(f"[Backend] Server is ready to accept connections on port {os.environ.get('PORT', '8000')}")

# Allow CORS for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for Chrome extension
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize SOAP client lazily to avoid startup crashes
_soap_client = None

def get_tradera_client():
    """Lazy initialization of SOAP client to prevent startup crashes."""
    global _soap_client
    if _soap_client is None:
        if not TRADERA_API_URL:
            raise ValueError("TRADERA_API_URL environment variable is not set")
        try:
            logging.info(f"[Backend] Initializing SOAP client for URL: {TRADERA_API_URL[:50]}...")
            _soap_client = Client(TRADERA_API_URL)
            logging.info("[Backend] SOAP client initialized successfully")
        except Exception as e:
            logging.error(f"[Backend] Failed to initialize SOAP client: {str(e)}")
            raise
    return _soap_client

@app.get("/")
async def root():
    """Root endpoint for Railway's default health checks."""
    return {
        "service": "Second-Hand Aggregation Finder (SHAF)",
        "status": "running",
        "version": "4.1",
        "endpoints": {
            "health": "/health",
            "related_products": "/related-products?product_name=<query>"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "tradera_configured": bool(TRADERA_API_URL and TRADERA_APP_ID and TRADERA_APP_KEY),
        "chromium_available": os.path.exists("/usr/bin/chromium"),
        "port": os.environ.get("PORT", "8000")
    }

def fetch_tradera_results(query: str):
    """Fetches relevant listings from Tradera API."""
    logging.info(f"[Backend] Fetching Tradera results for query: {query}")
    try:
        # Get SOAP client (lazy initialization)
        client = get_tradera_client()

        # Create Authentication Header
        auth_header = xsd.Element(
            '{http://api.tradera.com}AuthenticationHeader',
            xsd.ComplexType([
                xsd.Element('{http://api.tradera.com}AppId', xsd.String()),
                xsd.Element('{http://api.tradera.com}AppKey', xsd.String()),
            ])
        )
        header_value = auth_header(AppId=TRADERA_APP_ID, AppKey=TRADERA_APP_KEY)

        # Call Tradera API
        response = client.service.Search(
            query=query,
            categoryId=0,  # 0 = all categories
            pageNumber=1,
            orderBy="Relevance",
            _soapheaders=[header_value]
        )

        logging.info("[Backend] Received response from Tradera API.")

        # Parse and return results
        items = []
        if response and hasattr(response, "Items"):
            for item in response.Items[:3]:  # Get top 3 items
                max_bid = getattr(item, "MaxBid", None)
                buy_now_price = getattr(item, "BuyItNowPrice", None)

                price_info = "No price available"
                if max_bid is not None:
                    price_info = f"Max Bid: {max_bid} SEK"
                elif buy_now_price is not None:
                    price_info = f"Buy Now: {buy_now_price} SEK"

                items.append({
                    "title": getattr(item, "ShortDescription", "No title found"),
                    "price": price_info,
                    "link": getattr(item, "ItemUrl", "No link found"),
                    "image": getattr(item, "ThumbnailLink", ""),
                })

        logging.info(f"[Backend] Parsed {len(items)} results from Tradera.")
        return items if items else [{"message": "No items found"}]

    except Exception as e:
        logging.error(f"[Backend] Tradera API call failed: {str(e)}")
        return [{"error": f"Tradera API call failed: {str(e)}"}]

def get_driver():
    """Initialize Selenium WebDriver with proper error handling."""
    try:
        logging.info("[Backend] Initializing Selenium WebDriver...")
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1280,800")
        options.add_argument("--disable-blink-features=AutomationControlled")

        # Only set binary location if it exists (e.g., on Linux/Railway)
        linux_binary_path = "/usr/bin/chromium"
        linux_driver_path = "/usr/bin/chromedriver"
        
        if os.path.exists(linux_binary_path) and os.path.exists(linux_driver_path):
            # In Docker/Railway: Use installed chromium and chromedriver
            logging.info(f"[Backend] Using system Chromium: {linux_binary_path}")
            options.binary_location = linux_binary_path
            service = Service(executable_path=linux_driver_path)
        else:
            # Local Development: Use ChromeDriverManager
            logging.info("[Backend] Using ChromeDriverManager for local development")
            service = Service(ChromeDriverManager().install())

        driver = webdriver.Chrome(service=service, options=options)
        logging.info("[Backend] Selenium WebDriver initialized successfully")
        return driver
    except Exception as e:
        logging.error(f"[Backend] Failed to initialize Selenium WebDriver: {str(e)}")
        raise

def fetch_blocket_results(query: str):
    """Fetches relevant listings from Blocket by scraping the website."""
    logging.info(f"[Backend] Fetching Blocket results for query: {query}")
    driver = None
    try:
        driver = get_driver()
        url = f"https://www.blocket.se/annonser/hela_sverige?q={query}"
        driver.get(url)
        time.sleep(random.uniform(2, 5))  # Allow JavaScript to load
    except Exception as e:
        logging.warning(f"[Backend] Timeout/error waiting for Blocket results for {query}: {e}")
        if driver:
            driver.quit()
        return [{"error": f"Failed to fetch Blocket results: {str(e)}"}]

    soup = BeautifulSoup(driver.page_source, "html.parser")
    driver.quit()

    items = []
    for item in soup.select("article", limit=3):  # Get top 3 items
        title_element = item.select_one("h2")
        title = title_element.text.strip() if title_element else "No title found"

        price_element = item.select_one("div[class*='Price']")
        price = price_element.text.strip() if price_element else "No price found"

        if link_element:
            href = link_element["href"]
            link = href if href.startswith("http") else f"https://www.blocket.se{href}"
        else:
            link = "No link found"

        image_element = item.select_one("img")
        image = image_element["src"] if image_element else ""

        items.append({"title": title, "price": price, "link": link, "image": image})

    logging.info(f"[Backend] Parsed {len(items)} results from Blocket.")
    return items

def fetch_vinted_results(query: str):
    """Fetches relevant listings from Vinted by scraping the website."""
    logging.info(f"[Backend] Fetching vinted results for query: {query}")
    driver = None
    try:
        driver = get_driver()
        url = f"https://www.vinted.se/catalog?search_text={query}"
        driver.get(url)
        time.sleep(random.uniform(2, 5))  # Allow JavaScript to load
    except Exception as e:
        logging.warning(f"[Backend] Timeout/error waiting for Vinted results for {query}: {e}")
        if driver:
            driver.quit()
        return [{"error": "Failed to fetch Vinted results"}]

    soup = BeautifulSoup(driver.page_source, "html.parser")
    driver.quit()

    items = []
    for item in soup.select("article", limit=3):  # Get top 3 items
        title_element = item.select_one("h2")
        title = title_element.text.strip() if title_element else "No title found"

        price_element = item.select_one("div[class*='Price']")
        price = price_element.text.strip() if price_element else "No price found"

        if link_element:
            href = link_element["href"]
            link = href if href.startswith("http") else f"https://www.vinted.se{href}"
        else:
            link = "No link found"

        image_element = item.select_one("img")
        image = image_element["src"] if image_element else ""

        items.append({"title": title, "price": price, "link": link, "image": image})

    logging.info(f"[Backend] Parsed {len(items)} results from Blocket.")
    return items

@app.get("/related-products")
def get_related_products(product_name: str = Query(..., min_length=1)):
    """Handles incoming requests from the frontend to fetch related listings."""
    logging.info(f"[Backend] Received request for related products: {product_name}")

    try:
        tradera_results = fetch_tradera_results(product_name)
        logging.info("[Backend] Fetched Tradera results successfully.")

        blocket_results = fetch_blocket_results(product_name)
        logging.info("[Backend] Fetched Blocket results successfully.")

        return {
            "tradera": tradera_results,
            "blocket": blocket_results,
        }
    except Exception as e:
        logging.error(f"[Backend] Error fetching related products: {str(e)}")
        return {"error": str(e)}

# Only use to run locally
# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run("fetching_service:app", host="127.0.0.1", port=8000, reload=True)
