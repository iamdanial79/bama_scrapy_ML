import json
import os
import time
import random
import pandas as pd
from playwright.sync_api import sync_playwright

# Define output files
JSON_FILE = "bama_cars.json"
CSV_FILE = "bama_cars.csv"

# Function to scrape data
def scrape_bama():
    with sync_playwright() as p:
        browser = p.firefox.launch(headless=True)  # Headless for faster scraping
        context = browser.new_context(
            user_agent=random.choice([
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Linux; Android 10; SM-G970F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Mobile Safari/537.36",
                
            ])  # Rotating User-Agent
        )
        page = context.new_page()

        # Go to Bama car listings
        page.goto("https://bama.ir/car", timeout=80000)
        page.wait_for_load_state("networkidle")

        # Scroll to load more ads
        for _ in range(60):  # Increase for larger dataset
            page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
            time.sleep(random.uniform(2, 5))  # Random delay between scrolls

        # Locate ads
        ads = page.locator("a[href^='/car/detail']").all()
        print(f"Found {len(ads)} ads.")

        if not ads:
            print("No ads found. Exiting...")
            browser.close()
            return None

        # Load existing data to avoid duplicates
        if os.path.exists(JSON_FILE):
            with open(JSON_FILE, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
        else:
            existing_data = []

        existing_urls = {car["URL"] for car in existing_data}  # Avoid duplicates

        cars_data = existing_data  # Start with existing data

        for ad in ads:
            try:
                ad_url = ad.get_attribute("href")
                full_ad_url = f"https://bama.ir{ad_url}"

                if full_ad_url in existing_urls:
                    print(f"Skipping duplicate: {full_ad_url}")
                    continue

                # Open ad in a new tab
                new_page = context.new_page()
                new_page.goto(full_ad_url, timeout=70000)
                new_page.wait_for_load_state("networkidle")
                time.sleep(random.uniform(2.5, 6.0))  # Random delay to reduce bot detection

                # Extract price
                try:
                    price = new_page.locator("span.bama-ad-detail-price__price-text").inner_text()
                except:
                    price = "N/A"

                # Extract location
                try:
                    location = new_page.locator("span.address-text").inner_text()
                except:
                    location = "N/A"

                # Extract constant features
                features = {}
                feature_elements = new_page.locator("span[data-v-23e2e990]").all()
                value_elements = new_page.locator("p.dir-ltr").all()

                for i in range(len(feature_elements)):
                    try:
                        key = feature_elements[i].inner_text().strip()
                        value = value_elements[i].inner_text().strip()
                        features[key] = value
                    except IndexError:
                        continue  # Avoid missing elements

                # Extract variable features
                extra_feature_elements = new_page.locator("span.bama-vehicle-detail-with-link__row-title").all()
                extra_value_elements = new_page.locator("span.bama-vehicle-detail-with-link__row-text").all()

                for i in range(len(extra_feature_elements)):
                    try:
                        key = extra_feature_elements[i].inner_text().strip()
                        value = extra_value_elements[i].inner_text().strip()
                        features[key] = value
                    except IndexError:
                        continue  # Avoid missing elements

                # Extract description
                try:
                    description = new_page.locator("p[data-v-7980cec8]").inner_text()
                except:
                    description = "No description"

                # Save data
                car_data = {
                    "URL": full_ad_url,
                    "Price": price,
                    "Location": location,
                    "Description": description,
                    **features  # Merge extracted features dynamically
                }
                cars_data.append(car_data)
                existing_urls.add(full_ad_url)  # Avoid re-scraping same ad

                print(f"Scraped: {car_data}")

                new_page.close()  # Close the tab

            except Exception as e:
                print(f"Error scraping ad: {e}")
                new_page.close()

        browser.close()

        # Save updated data as JSON
        with open(JSON_FILE, "w", encoding="utf-8") as f:
            json.dump(cars_data, f, ensure_ascii=False, indent=4)

        print(f"Data saved to {JSON_FILE}")

        return JSON_FILE

# Convert JSON to CSV (Append Mode)
def convert_json_to_csv(json_file):
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    df = pd.DataFrame(data)

    # Append to existing CSV if it exists
    if os.path.exists(CSV_FILE):
        df_existing = pd.read_csv(CSV_FILE)
        df = pd.concat([df_existing, df]).drop_duplicates(subset=["URL"], keep="last")

    df.to_csv(CSV_FILE, index=False, encoding="utf-8")

    print(f"CSV updated and saved to {CSV_FILE}")
    print("\nPreview of CSV:\n", df.head())

# Run scraper & update CSV
json_file = scrape_bama()
if json_file:
    convert_json_to_csv(json_file)
    