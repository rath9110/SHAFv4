from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import logging
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import random
import asyncio
from bs4 import BeautifulSoup
from zeep import Client, xsd
import shutil
from fastapi import FastAPI, Query
import logging
import os
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

TRADERA_API_URL = os.environ.get("TRADERA_API_URL")
TRADERA_APP_ID = os.environ.get("TRADERA_APP_ID")
TRADERA_APP_KEY = os.environ.get("TRADERA_APP_KEY")

app = FastAPI()

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

app = FastAPI()

# Allow CORS for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["chrome-extension://<your-extension-id>", "http://localhost:3000"],  # Update with actual extension ID
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

# Initialize SOAP client
client = Client(TRADERA_API_URL)

def fetch_tradera_results(query: str):
    """Fetches relevant listings from Tradera API."""
    logging.info(f"[Backend] Fetching Tradera results for query: {query}")
    try:
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
        return [{"error": "An error occurred while fetching Tradera results."}]

def get_driver():
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
        options.binary_location = linux_binary_path
        service = Service(executable_path=linux_driver_path)
    else:
        # Local Development: Use ChromeDriverManager
        service = Service(ChromeDriverManager().install())

    driver = webdriver.Chrome(service=service, options=options)
    return driver

def fetch_blocket_results(query: str):
    """Fetches relevant listings from Blocket by scraping the website."""
    logging.info(f"[Backend] Fetching Blocket results for query: {query}")
    driver = get_driver()
    url = f"https://www.blocket.se/annonser/hela_sverige?q={query}"
    driver.get(url)
    
    try:
        # Wait for articles to load instead of hard sleep
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "article"))
        )
    except Exception:
        logging.warning(f"[Backend] Timeout waiting for Blocket results for {query}")

    soup = BeautifulSoup(driver.page_source, "html.parser")
    driver.quit()

    items = []
    for item in soup.select("article", limit=3):  # Get top 3 items
        title_element = item.select_one("h2")
        title = title_element.text.strip() if title_element else "No title found"

        price_element = item.select_one("div[class*='Price']")
        price = price_element.text.strip() if price_element else "No price found"

        link_element = item.select_one("a")
        link = "https://www.blocket.se" + link_element["href"] if link_element else "No link found"

        image_element = item.select_one("img")
        image = image_element["src"] if image_element else ""

        items.append({"title": title, "price": price, "link": link, "image": image})

    logging.info(f"[Backend] Parsed {len(items)} results from Blocket.")
    return items

def fetch_vinted_results(query: str):
    """Fetches relevant listings from Vinted by scraping the website."""
    logging.info(f"[Backend] Fetching vinted results for query: {query}")
    driver = get_driver()
    url = f"https://www.vinted.se/catalog?search_text={query}"
    driver.get(url)
    
    try:
        # Wait for articles to load instead of hard sleep
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "article"))
        )
    except Exception:
        logging.warning(f"[Backend] Timeout waiting for Vinted results for {query}")

    soup = BeautifulSoup(driver.page_source, "html.parser")
    driver.quit()

    items = []
    for item in soup.select("article", limit=3):  # Get top 3 items
        title_element = item.select_one("h2")
        title = title_element.text.strip() if title_element else "No title found"

        price_element = item.select_one("div[class*='Price']")
        price = price_element.text.strip() if price_element else "No price found"

        link_element = item.select_one("a")
        link = "https://www.blocket.se" + link_element["href"] if link_element else "No link found"

        image_element = item.select_one("img")
        image = image_element["src"] if image_element else ""

        items.append({"title": title, "price": price, "link": link, "image": image})

    logging.info(f"[Backend] Parsed {len(items)} results from Blocket.")
    return items

@app.get("/related-products")
async def get_related_products(product_name: str = Query(..., min_length=1)):
    """Handles incoming requests from the frontend to fetch related listings."""
    logging.info(f"[Backend] Received request for related products: {product_name}")

    try:
        # Run fetching tasks in parallel
        tradera_task = asyncio.to_thread(fetch_tradera_results, product_name)
        blocket_task = asyncio.to_thread(fetch_blocket_results, product_name)
        
        tradera_results, blocket_results = await asyncio.gather(tradera_task, blocket_task)

        logging.info("[Backend] Fetched results successfully.")

        return {
            "tradera": tradera_results,
            "blocket": blocket_results,
        }
    except Exception as e:
        logging.error(f"[Backend] Error fetching related products: {str(e)}")
        return {"error": "An internal error occurred."}

#Only use to run locally
#if __name__ == "__main__":
#    import uvicorn
#    uvicorn.run("fetching_service:app", host="127.0.0.1", port=8000, reload=True)

