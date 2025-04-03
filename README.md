# Amazon Review Scraper

This script scrapes Amazon product reviews, filtering by star rating, and saves
them to CSV files in a product-specific folder. It also combines all reviews for
a product into a single `combined_reviews.csv` file.

## Features
- Scrapes reviews for a specified star rating (1-5) or all reviews.
- Organizes reviews into product-specific folders (e.g., `reviews_EXAMPLEASIN`).
- Combines all reviews for a product into a single `combined_reviews.csv` file.
- Includes anti-detection measures (random delays, user-agent rotation,
  human-like behavior).
- Handles Ctrl+C gracefully, saving partial reviews.
- Accepts the product URL as a command-line argument.

## Requirements
- Python 3.x
- Selenium (`pip install selenium`)
- BeautifulSoup (`pip install beautifulsoup4`)
- Pandas (`pip install pandas`)
- ChromeDriver (installed at `/usr/local/bin/chromedriver`)

## Usage
```bash
1. Run the script with a product URL as a command-line argument:
   python3 amazon_review_scraper.py https://www.amazon.com/product/dp/EXAMPLEASIN
2. Enter the star rating (1, 2, 3, 4, 5, or 0 for all reviews) when prompted.
3. Log in to Amazon manually if prompted (including 2FA).
4. The script will scrape up to 5 pages of reviews, save them to a product-specific
   folder (e.g., `reviews_EXAMPLEASIN/amazon_reviews_4_star.csv`), and combine all
   reviews into `combined_reviews.csv`.

## Notes
- Use a residential IP address to avoid being flagged by Amazon.
- Scrape in moderation to avoid account suspension (limited to 5 pages per run).
- To change the maximum number of pages scraped, modify the `max_pages` parameter in the `scrape_amazon_reviews` function call in `amazon_review_scraper.py`. For example, change `max_pages=5` to `max_pages=10` to scrape up to 10 pages.
- Monitor your Amazon account for warnings.
- The script saves cookies to `amazon_cookies.pkl` for reuse, which is excluded from the repository via `.gitignore`.
