from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
from bs4 import BeautifulSoup
import time
import pickle
import os
import random
import signal
import sys
import glob
import argparse

# List of user-agents to rotate
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/114.0",
]

# Function to handle Ctrl+C gracefully
def signal_handler(sig, frame, driver=None, reviews=None, product_folder=""):
    print("\nYou pressed Ctrl+C! Exiting gracefully...")
    if driver:
        driver.quit()
    if reviews:
        print("Saving collected reviews before exiting...")
        save_to_csv(reviews, default_filename=os.path.join(product_folder, "amazon_reviews_partial.csv"))
    sys.exit(0)

# Function to simulate human-like behavior
def simulate_human_behavior(driver):
    try:
        # Scroll to the bottom of the page
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(random.uniform(1, 3))  # Random pause after scrolling
        # Scroll back up slightly
        driver.execute_script("window.scrollBy(0, -200);")
        time.sleep(random.uniform(0.5, 1.5))  # Random pause after scrolling
    except Exception as e:
        print(f"Error simulating human behavior: {e}")

# Function to extract ASIN from the product URL
def extract_asin(product_url):
    try:
        # The ASIN is typically in the URL after "/dp/" or in the format "/product-reviews/"
        if "/dp/" in product_url:
            asin = product_url.split("/dp/")[1].split("/")[0].split("?")[0]
        elif "/product-reviews/" in product_url:
            asin = product_url.split("/product-reviews/")[1].split("/")[0].split("?")[0]
        else:
            raise ValueError("Could not find ASIN in the product URL.")
        return asin
    except Exception as e:
        print(f"Error extracting ASIN: {e}")
        return "unknown_product"

# Function to scrape reviews from an Amazon product page
def scrape_amazon_reviews(product_url, star_rating=None, max_pages=5):
    # Extract ASIN from the product URL
    asin = extract_asin(product_url)
    product_folder = f"reviews_{asin}"
    
    # Create a folder for the product if it doesn't exist
    if not os.path.exists(product_folder):
        os.makedirs(product_folder)
        print(f"Created folder: {product_folder}")

    # Map star rating to Amazon's filterByStar value
    star_mapping = {
        1: "one_star",
        2: "two_star",
        3: "three_star",
        4: "four_star",
        5: "five_star"
    }

    if star_rating is not None and star_rating not in star_mapping:
        print(f"Invalid star rating: {star_rating}. Please use 1, 2, 3, 4, or 5.")
        return []

    # Set up Selenium with ChromeDriver
    chrome_options = Options()
    # chrome_options.add_argument("--headless")  # Run in background (commented for debugging)
    chrome_options.add_argument(f"user-agent={random.choice(USER_AGENTS)}")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    service = Service(executable_path="/usr/local/bin/chromedriver")
    try:
        driver = webdriver.Chrome(service=service, options=chrome_options)
    except Exception as e:
        print(f"Failed to initialize ChromeDriver: {e}")
        return []

    reviews = []
    page = 1

    # Register the signal handler for Ctrl+C
    signal.signal(signal.SIGINT, lambda sig, frame: signal_handler(sig, frame, driver, reviews, product_folder))

    try:
        # Load cookies if they exist
        if os.path.exists("amazon_cookies.pkl"):
            print("Loading cookies...")
            driver.get("https://www.amazon.com")
            for cookie in pickle.load(open("amazon_cookies.pkl", "rb")):
                driver.add_cookie(cookie)
            driver.refresh()
        else:
            print("No cookies found. Please log in manually.")

        # Start with the product page
        print(f"Loading product page: {product_url}")
        driver.get(product_url)
        time.sleep(random.uniform(2, 5))

        # Check if redirected to login page
        print("Checking for login page...")
        try:
            email_field = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "ap_email"))
            )
            print("Login page detected. Please log in manually...")
        except:
            print("No login page detected, proceeding...")

        # Pause to allow manual login (including 2FA)
        print("Please log in to Amazon if prompted (including 2FA if required).")
        print("Press Enter in the terminal when you're logged in and the product page is fully loaded...")
        input()

        # Save cookies after login
        print("Saving cookies...")
        pickle.dump(driver.get_cookies(), open("amazon_cookies.pkl", "wb"))

        # Ensure the product page is loaded
        print("Verifying product page is loaded...")
        WebDriverWait(driver, 10).until(
            EC.url_contains("/dp/")
        )
        print(f"Current URL: {driver.current_url}")

        # Simulate human behavior
        simulate_human_behavior(driver)

        # Wait for the "See more reviews" link
        print("Looking for 'See more reviews' link...")
        try:
            see_all_reviews = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//a[@data-hook='see-all-reviews-link-foot']"))
            )
            print("Found 'See more reviews' link!")
        except Exception as e:
            print(f"Failed to find 'See more reviews' link: {e}")
            print("Page source for debugging:")
            print(driver.page_source[:2000])
            print("Press Enter to close the browser...")
            input()
            return []

        reviews_url = see_all_reviews.get_attribute("href")
        print(f"Navigating to reviews page: {reviews_url}")

        # Apply star rating filter if specified
        if star_rating is not None:
            star_filter = star_mapping[star_rating]
            if "filterByStar" not in reviews_url:
                if "?" in reviews_url:
                    reviews_url = f"{reviews_url}&filterByStar={star_filter}"
                else:
                    reviews_url = f"{reviews_url}?filterByStar={star_filter}"
            print(f"Navigating to filtered reviews page: {reviews_url}")
            driver.get(reviews_url)
        else:
            print("No star rating filter applied. Scraping all reviews.")
            driver.get(reviews_url)

        time.sleep(random.uniform(2, 5))

        while page <= max_pages:
            # Wait for the reviews page to load
            print(f"Waiting for reviews to load on page {page}...")
            try:
                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.XPATH, "//div[starts-with(@id, 'customer_review-')]"))
                )
                print(f"Reviews page {page} loaded successfully!")
            except Exception as e:
                print(f"Failed to load reviews on page {page}: {e}")
                print("Page source for debugging:")
                print(driver.page_source[:2000])
                print("Please inspect the page manually to see if reviews are present.")
                print("Press Enter to continue and attempt to scrape anyway...")
                input()

            # Simulate human behavior
            simulate_human_behavior(driver)

            # Scrape reviews on the current page
            print(f"Scraping page {page}...")
            soup = BeautifulSoup(driver.page_source, "html.parser")
            review_blocks = soup.find_all("div", id=lambda x: x and x.startswith("customer_review-"))

            if not review_blocks:
                print("No review blocks found on this page.")
                print("Page source for debugging:")
                print(driver.page_source[:2000])
                print("Press Enter to close the browser...")
                input()
                break

            for review in review_blocks:
                try:
                    reviewer = review.find("span", class_="a-profile-name").text.strip()
                    rating = review.find("i", {"data-hook": "review-star-rating"}).text.strip()
                    date = review.find("span", {"data-hook": "review-date"}).text.strip()
                    text = review.find("span", {"data-hook": "review-body"}).text.strip()

                    reviews.append({
                        "Reviewer": reviewer,
                        "Rating": rating,
                        "Date": date,
                        "Review": text
                    })
                except AttributeError as e:
                    print(f"Error parsing review: {e}")
                    continue

            # Check for next page
            print(f"Looking for 'Next' button on page {page}...")
            try:
                simulate_human_behavior(driver)
                next_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//li[@class='a-last']/a | //a[@data-hook='pagination-bar-next']"))
                )
                next_url = next_button.get_attribute("href")
                print(f"Found 'Next' button. Navigating to next page: {next_url}")
                driver.get(next_url)
                page += 1
                time.sleep(random.uniform(2, 5))
            except Exception as e:
                print(f"No more pages to scrape: {e}")
                break

    except Exception as e:
        print(f"Error occurred: {e}")
        print("Press Enter to close the browser...")
        input()
    finally:
        driver.quit()

    return reviews, product_folder

# Function to save reviews to CSV in the product folder
def save_to_csv(reviews, default_filename):
    if not reviews:
        print("No reviews to save.")
        return

    # Convert reviews to a DataFrame
    df = pd.DataFrame(reviews)

    # Save the DataFrame to the specified file
    df.to_csv(default_filename, index=False)
    print(f"Saved {len(reviews)} reviews to {default_filename}")

# Function to combine all CSV files in the product folder
def combine_csv_files(product_folder):
    # Find all CSV files in the product folder, excluding combined_reviews.csv and partial files
    csv_files = glob.glob(os.path.join(product_folder, "amazon_reviews_*.csv"))
    csv_files = [f for f in csv_files if "partial" not in f and "combined" not in f]

    if not csv_files:
        print(f"No CSV files found in {product_folder} to combine.")
        return

    # Combine all CSV files into one
    combined_df = pd.concat((pd.read_csv(f) for f in csv_files), ignore_index=True)
    combined_filename = os.path.join(product_folder, "combined_reviews.csv")
    combined_df.to_csv(combined_filename, index=False)
    print(f"Combined {len(csv_files)} CSV files into {combined_filename}")

# Main execution
if __name__ == "__main__":
    # Set up command-line argument parsing
    parser = argparse.ArgumentParser(description="Scrape Amazon product reviews.")
    parser.add_argument("product_url", help="The Amazon product URL to scrape reviews from")
    args = parser.parse_args()

    # Prompt user for star rating
    print("Enter the star rating to filter reviews (1, 2, 3, 4, 5, or 0 for all reviews):")
    try:
        star_rating_input = int(input())
        if star_rating_input == 0:
            star_rating = None  # Scrape all reviews
        elif star_rating_input in [1, 2, 3, 4, 5]:
            star_rating = star_rating_input
        else:
            print("Invalid input. Please enter 1, 2, 3, 4, 5, or 0.")
            exit()
    except ValueError:
        print("Invalid input. Please enter a number (1, 2, 3, 4, 5, or 0).")
        exit()

    # Scrape reviews
    reviews, product_folder = scrape_amazon_reviews(args.product_url, star_rating=star_rating, max_pages=5)
    
    # Save to CSV in the product folder
    if reviews:
        if star_rating is None:
            save_to_csv(reviews, default_filename=os.path.join(product_folder, "amazon_reviews_all.csv"))
        else:
            save_to_csv(reviews, default_filename=os.path.join(product_folder, f"amazon_reviews_{star_rating}_star.csv"))
        
        # Combine all CSV files in the product folder
        combine_csv_files(product_folder)
    else:
        print("No reviews scraped.")