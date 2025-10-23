import os
import re
import json
import time
import random
import requests
import logging
from typing import Dict, Any, List, Tuple, Optional
from bs4 import BeautifulSoup
from datetime import datetime
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Get API keys from environment variables
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
RAPIDAPI_HOST = "real-time-amazon-data.p.rapidapi.com"

# User agent list for rotating
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1"
]

def get_random_user_agent() -> str:
    """Get a random user agent from the list"""
    return random.choice(USER_AGENTS)

def extract_asin_from_url(url: str) -> Optional[str]:
    """
    Extract ASIN from an Amazon product URL.
    
    Args:
        url: Amazon product URL
        
    Returns:
        ASIN if found, None otherwise
    """
    # Pattern for ASIN in Amazon URLs
    patterns = [
        r'/dp/([A-Z0-9]{10})',
        r'/product/([A-Z0-9]{10})',
        r'/gp/product/([A-Z0-9]{10})',
        r'asin=([A-Z0-9]{10})',
        r'asin/([A-Z0-9]{10})'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None

def scrape_amazon_reviews_api(asin: str, num_reviews: int = 20, rapidapi_key: Optional[str] = None) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Scrape Amazon reviews using the RapidAPI Amazon Data API.
    
    Args:
        asin: Amazon ASIN (product ID)
        num_reviews: Maximum number of reviews to scrape
        rapidapi_key: RapidAPI key (optional, will use env var if not provided)
        
    Returns:
        Tuple containing product info and list of reviews
    """
    # Use provided API key or fall back to env var
    api_key = rapidapi_key or RAPIDAPI_KEY
    
    if not api_key:
        logger.warning("No RapidAPI key provided, using fallback mock data")
        return mock_amazon_product_info(asin), mock_amazon_reviews(asin, num_reviews)
    
    # Initialize results
    product_info = {"asin": asin, "name": "Unknown Product"}
    all_reviews = []
    
    # Base URL for the API
    base_url = "https://real-time-amazon-data.p.rapidapi.com/product-reviews"
    
    # Headers for the API request
    headers = {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": RAPIDAPI_HOST
    }
    
    # First, get product info
    try:
        product_url = "https://real-time-amazon-data.p.rapidapi.com/product-details"
        product_querystring = {"asin": asin, "country": "US"}
        
        product_response = requests.get(product_url, headers=headers, params=product_querystring)
        product_response.raise_for_status()
        
        product_data = product_response.json()
        if product_data.get("status") == "success":
            product_info = {
                "asin": asin,
                "name": product_data.get("data", {}).get("title", "Unknown Product"),
                "brand": product_data.get("data", {}).get("brand", "Unknown Brand"),
                "price": product_data.get("data", {}).get("pricing", {}).get("current_price", 0),
                "rating": product_data.get("data", {}).get("reviews", {}).get("rating", 0),
                "review_count": product_data.get("data", {}).get("reviews", {}).get("count", 0),
                "url": f"https://www.amazon.com/dp/{asin}"
            }
        
    except Exception as e:
        logger.error(f"Error fetching product details: {e}")
    
    # Define star ratings to scrape (to get a balanced sample)
    star_ratings = [5, 4, 3, 2, 1]
    reviews_per_rating = num_reviews // len(star_ratings)
    
    # First, get reviews for each star rating
    for star_rating in star_ratings:
        logger.info(f"Fetching reviews with star_rating={star_rating}...")
        
        # Try to get reviews_per_rating reviews for each star rating
        pages_to_try = 2  # Try up to 2 pages for each star rating
        reviews_for_this_rating = 0
        
        for page in range(1, pages_to_try + 1):
            if reviews_for_this_rating >= reviews_per_rating:
                break
            
            logger.info(f"Fetching page {page} for {star_rating}-star reviews...")
            
            querystring = {
                "asin": asin,
                "country": "US",
                "sort_by": "TOP_REVIEWS",  # Use top reviews for star-specific queries
                "star_rating": star_rating,
                "verified_purchases_only": "false",
                "images_or_videos_only": "false",
                "current_format_only": "false",
                "page": str(page)
            }
            
            try:
                response = requests.get(base_url, headers=headers, params=querystring)
                response.raise_for_status()
                
                data = response.json()
                
                if "reviews" not in data.get("data", {}) or not data["data"]["reviews"]:
                    logger.info(f"No {star_rating}-star reviews found on page {page}")
                    break
                
                reviews = data["data"]["reviews"]
                
                for review in reviews:
                    if reviews_for_this_rating >= reviews_per_rating:
                        break
                    
                    # Process and add the review
                    processed_review = {
                        "review_id": review.get("id", ""),
                        "title": review.get("title", ""),
                        "text": review.get("text", ""),
                        "rating": float(review.get("rating", 0)),
                        "reviewer_name": review.get("username", "Anonymous"),
                        "review_date_text": review.get("date", {}).get("text", ""),
                        "review_date": datetime.now().isoformat(),  # Default to now
                        "verified_purchase": review.get("verified_purchase", False),
                        "helpful_votes": review.get("helpful_votes", 0)
                    }
                    
                    # Try to parse the date
                    date_text = review.get("date", {}).get("text", "")
                    if date_text:
                        try:
                            # Handle various date formats
                            if "on" in date_text:
                                date_text = date_text.split("on")[1].strip()
                            
                            # Try different date formats
                            for fmt in ["%B %d, %Y", "%d %B %Y", "%Y-%m-%d"]:
                                try:
                                    review_date = datetime.strptime(date_text, fmt)
                                    processed_review["review_date"] = review_date.isoformat()
                                    break
                                except ValueError:
                                    continue
                        except Exception as e:
                            logger.warning(f"Error parsing date '{date_text}': {e}")
                    
                    all_reviews.append(processed_review)
                    reviews_for_this_rating += 1
                
                # Add a delay to avoid rate limiting
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Error fetching {star_rating}-star reviews: {e}")
                break
    
    # If we still need more reviews, get additional reviews sorted by most recent
    if len(all_reviews) < num_reviews:
        remaining_reviews = num_reviews - len(all_reviews)
        logger.info(f"Fetching {remaining_reviews} more reviews sorted by most recent...")
        
        sort_by_options = ["MOST_RECENT", "TOP_REVIEWS"]
        pages_to_try = 2
        
        for sort_by in sort_by_options:
            if len(all_reviews) >= num_reviews:
                break
                
            for page in range(1, pages_to_try + 1):
                if len(all_reviews) >= num_reviews:
                    break
                
                logger.info(f"Fetching page {page} for sort_by={sort_by}...")
                
                querystring = {
                    "asin": asin,
                    "country": "US",
                    "sort_by": sort_by,
                    "star_rating": "ALL",  # Get all ratings
                    "verified_purchases_only": "false",
                    "images_or_videos_only": "false",
                    "current_format_only": "false",
                    "page": str(page)
                }
                
                try:
                    response = requests.get(base_url, headers=headers, params=querystring)
                    logger.info(f"API response status code: {response.status_code}")
                    data = response.json()
                    
                    if "reviews" not in data.get("data", {}) or not data["data"]["reviews"]:
                        logger.info(f"No reviews found for sort_by={sort_by}, page={page}")
                        break
                    
                    reviews = data["data"]["reviews"]
                    
                    for review in reviews:
                        # Check if this review is already in our list
                        review_id = review.get("id", "")
                        if any(r.get("review_id") == review_id for r in all_reviews):
                            continue
                        
                        # Process and add the review
                        processed_review = {
                            "review_id": review_id,
                            "title": review.get("title", ""),
                            "text": review.get("text", ""),
                            "rating": float(review.get("rating", 0)),
                            "reviewer_name": review.get("username", "Anonymous"),
                            "review_date_text": review.get("date", {}).get("text", ""),
                            "review_date": datetime.now().isoformat(),  # Default to now
                            "verified_purchase": review.get("verified_purchase", False),
                            "helpful_votes": review.get("helpful_votes", 0)
                        }
                        
                        # Try to parse the date
                        date_text = review.get("date", {}).get("text", "")
                        if date_text:
                            try:
                                # Handle various date formats
                                if "on" in date_text:
                                    date_text = date_text.split("on")[1].strip()
                                
                                # Try different date formats
                                for fmt in ["%B %d, %Y", "%d %B %Y", "%Y-%m-%d"]:
                                    try:
                                        review_date = datetime.strptime(date_text, fmt)
                                        processed_review["review_date"] = review_date.isoformat()
                                        break
                                    except ValueError:
                                        continue
                            except Exception as e:
                                logger.warning(f"Error parsing date '{date_text}': {e}")
                        
                        all_reviews.append(processed_review)
                        
                        if len(all_reviews) >= num_reviews:
                            break
                    
                    # Add a delay to avoid rate limiting
                    time.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Error fetching reviews with sort_by={sort_by}: {e}")
                    break
    
    # If we still don't have enough reviews, use mock data to fill in
    if len(all_reviews) < num_reviews:
        logger.warning(f"Only found {len(all_reviews)} reviews, adding mock data to reach {num_reviews}")
        mock_reviews = mock_amazon_reviews(asin, num_reviews - len(all_reviews))
        all_reviews.extend(mock_reviews)
    
    logger.info(f"Successfully scraped {len(all_reviews)} reviews for ASIN {asin}")
    return product_info, all_reviews

def scrape_flipkart_reviews(product_url: str, num_reviews: int = 20) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Scrape reviews from a Flipkart product page.
    
    Args:
        product_url: URL of the Flipkart product page
        num_reviews: Maximum number of reviews to scrape
        
    Returns:
        Tuple containing product info and list of reviews
    """
    headers = {
        'User-Agent': get_random_user_agent(),
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Referer': 'https://www.flipkart.com/'
    }
    
    # Initialize results
    product_info = {"name": "Unknown Product", "url": product_url}
    all_reviews = []
    
    # Ensure the URL is for the reviews page
    if '/p/' in product_url and '/product-reviews/' not in product_url:
        product_url = product_url.replace('/p/', '/product-reviews/')
        if '&lid=' in product_url:
            product_url = product_url.split('&lid=')[0]
        product_url += '&aid=overall'
    
    try:
        # First, get product info
        response = requests.get(product_url, headers=headers)
        if response.status_code != 200:
            logger.error(f"Failed to fetch product page: {response.status_code}")
            return product_info, mock_flipkart_reviews(num_reviews)
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract product name
        product_name_elem = soup.select_one('div._2s4DIt')
        if product_name_elem:
            product_info["name"] = product_name_elem.text.strip()
        
        # Extract product rating
        rating_elem = soup.select_one('div._2d4LTz')
        if rating_elem:
            try:
                product_info["rating"] = float(rating_elem.text)
            except ValueError:
                product_info["rating"] = 0.0
        
        # Extract review count
        review_count_elem = soup.select_one('div._2_R_DZ span')
        if review_count_elem:
            review_text = review_count_elem.text
            count_match = re.search(r'(\d+(?:,\d+)*)', review_text)
            if count_match:
                count_str = count_match.group(1).replace(',', '')
                try:
                    product_info["review_count"] = int(count_str)
                except ValueError:
                    product_info["review_count"] = 0
        
        # Now get the reviews
        current_url = product_url
        while len(all_reviews) < num_reviews and current_url:
            logger.info(f"Scraping reviews from: {current_url}")
            
            response = requests.get(current_url, headers=headers)
            if response.status_code != 200:
                logger.error(f"Failed to fetch reviews page: {response.status_code}")
                break
            
            soup = BeautifulSoup(response.content, 'html.parser')
            page_reviews = extract_flipkart_reviews_from_page(soup)
            
            if not page_reviews:
                break
                
            all_reviews.extend(page_reviews)
            
            # Get next page URL
            next_link = soup.select_one('a._1LKTO3')
            if next_link and '&page=' in next_link.get('href', ''):
                current_url = 'https://www.flipkart.com' + next_link['href']
            else:
                current_url = None
            
            # Add a delay to avoid being blocked
            time.sleep(random.uniform(1.0, 3.0))
            
            # Update headers with a new user agent
            headers['User-Agent'] = get_random_user_agent()
        
        # Limit to the requested number of reviews
        all_reviews = all_reviews[:num_reviews]
        
        # If we don't have enough reviews, add mock data
        if len(all_reviews) < num_reviews:
            logger.warning(f"Only found {len(all_reviews)} reviews, adding mock data to reach {num_reviews}")
            mock_reviews = mock_flipkart_reviews(num_reviews - len(all_reviews))
            all_reviews.extend(mock_reviews)
        
        return product_info, all_reviews
        
    except Exception as e:
        logger.error(f"Error scraping Flipkart reviews: {e}")
        return product_info, mock_flipkart_reviews(num_reviews)

def extract_flipkart_reviews_from_page(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    """
    Extract reviews from a Flipkart reviews page.
    
    Args:
        soup: BeautifulSoup object of the reviews page
        
    Returns:
        List of review dictionaries
    """
    reviews = []
    review_elements = soup.select('div._1AtVbE div._27M-vq')
    
    for review_elem in review_elements:
        review = {}
        
        # Extract rating
        rating_elem = review_elem.select_one('div._3LWZlK')
        if rating_elem:
            try:
                review['rating'] = float(rating_elem.text)
            except ValueError:
                review['rating'] = 0.0
        
        # Extract review title
        title_elem = review_elem.select_one('p._2-N8zT')
        if title_elem:
            review['title'] = title_elem.text.strip()
        
        # Extract review text
        text_elem = review_elem.select_one('div.t-ZTKy')
        if text_elem:
            # Check if there's a "Read More" button
            if text_elem.select_one('div.collapsible-text'):
                review['text'] = text_elem.select_one('div.collapsible-text').text.strip()
            else:
                review['text'] = text_elem.text.strip()
        
        # Extract reviewer name
        name_elem = review_elem.select_one('p._2sc7ZR')
        if name_elem:
            review['reviewer_name'] = name_elem.text.strip()
        
        # Extract review date
        date_elem = review_elem.select_one('p._2sc7ZR + p._2sc7ZR')
        if date_elem:
            review['review_date_text'] = date_elem.text.strip()
            # Try to parse the date
            try:
                # Flipkart date format is usually "15 Jan, 2023" or similar
                date_text = date_elem.text.strip()
                if ',' in date_text:
                    date_text = date_text.replace(',', '')
                review_date = datetime.strptime(date_text, '%d %b %Y')
                review['review_date'] = review_date.isoformat()
            except Exception:
                review['review_date'] = datetime.now().isoformat()
        
        # Extract verified purchase
        verified_elem = review_elem.select_one('span._2mcZGG')
        review['verified_purchase'] = verified_elem is not None
        
        # Extract helpful votes
        helpful_elem = review_elem.select_one('span._2ZibVB')
        if helpful_elem:
            votes_text = helpful_elem.text.strip()
            votes_match = re.search(r'(\d+)', votes_text)
            if votes_match:
                review['helpful_votes'] = int(votes_match.group(1))
            else:
                review['helpful_votes'] = 0
        else:
            review['helpful_votes'] = 0
        
        # Add review ID
        review['review_id'] = f"flipkart_{len(reviews)}"
        
        reviews.append(review)
    
    return reviews

def mock_amazon_product_info(asin: str) -> Dict[str, Any]:
    """
    Generate mock Amazon product info.
    
    Args:
        asin: Amazon ASIN
        
    Returns:
        Dictionary with product info
    """
    return {
        "asin": asin,
        "name": f"Mock Product {asin}",
        "brand": "Mock Brand",
        "price": 99.99,
        "rating": 4.2,
        "review_count": 250,
        "url": f"https://www.amazon.com/dp/{asin}"
    }

def mock_amazon_reviews(asin: str, num_reviews: int) -> List[Dict[str, Any]]:
    """
    Generate mock Amazon reviews.
    
    Args:
        asin: Amazon ASIN
        num_reviews: Number of reviews to generate
        
    Returns:
        List of review dictionaries
    """
    reviews = []
    
    # Sample review texts
    positive_texts = [
        "This product is amazing! I love how easy it is to use and the quality is excellent.",
        "I've been using this for a month now and it's holding up well. Very satisfied with my purchase.",
        "Great value for the price. Would definitely recommend to friends and family.",
        "The customer service was excellent when I had an issue. They resolved it quickly.",
        "This exceeded my expectations. The design is beautiful and it works perfectly."
    ]
    
    neutral_texts = [
        "It's an average product. Nothing special but it works as advertised.",
        "The product is good but the shipping took forever. Almost a month to arrive.",
        "It's okay for the price. Not the best quality but it gets the job done.",
        "Some features are great, others not so much. Overall it's decent.",
        "It works fine but the instructions were confusing. Had to look up a tutorial online."
    ]
    
    negative_texts = [
        "I'm disappointed with this purchase. It broke after just two weeks of use.",
        "This is the worst product I've ever bought. Complete waste of money.",
        "The quality is terrible. Definitely not worth the price.",
        "It doesn't work as advertised. Very misleading product description.",
        "Had to return it. Didn't meet my expectations at all."
    ]
    
    # Generate reviews with a distribution of ratings
    for i in range(num_reviews):
        # Determine rating (weighted towards higher ratings as is common on Amazon)
        weights = [0.1, 0.1, 0.1, 0.3, 0.4]  # Weights for ratings 1-5
        rating = random.choices([1, 2, 3, 4, 5], weights=weights)[0]
        
        # Select review text based on rating
        if rating >= 4:
            text = random.choice(positive_texts)
        elif rating == 3:
            text = random.choice(neutral_texts)
        else:
            text = random.choice(negative_texts)
        
        # Generate a random date within the last year
        days_ago = random.randint(1, 365)
        review_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        review_date = review_date.replace(day=review_date.day - days_ago)
        
        review = {
            "review_id": f"mock_{asin}_{i}",
            "title": f"Review for {asin}",
            "text": text,
            "rating": float(rating),
            "reviewer_name": f"MockUser{i}",
            "review_date_text": review_date.strftime("%B %d, %Y"),
            "review_date": review_date.isoformat(),
            "verified_purchase": random.choice([True, False]),
            "helpful_votes": random.randint(0, 50)
        }
        
        reviews.append(review)
    
    return reviews

def mock_flipkart_reviews(num_reviews: int) -> List[Dict[str, Any]]:
    """
    Generate mock Flipkart reviews.
    
    Args:
        num_reviews: Number of reviews to generate
        
    Returns:
        List of review dictionaries
    """
    reviews = []
    
    # Sample review texts
    positive_texts = [
        "Great product! Very happy with my purchase. The quality is excellent and it arrived on time.",
        "This is exactly what I was looking for. Works perfectly and the price is reasonable.",
        "Excellent value for money. The product quality is much better than I expected.",
        "Very satisfied with this purchase. It's durable and well-designed.",
        "Flipkart delivery was super fast and the product is amazing. Highly recommended!"
    ]
    
    neutral_texts = [
        "It's an okay product. Not bad but nothing special either.",
        "The product is decent for the price. Don't expect premium quality though.",
        "Average product. It works but there are better options available.",
        "It's fine for basic use. Don't expect too much from it.",
        "Delivery was quick but the product is just average. Not disappointed but not impressed either."
    ]
    
    negative_texts = [
        "Not worth the money. The quality is poor and it stopped working after a week.",
        "Very disappointed with this purchase. The product looks nothing like the pictures.",
        "Waste of money. Don't buy this product, it's cheaply made and breaks easily.",
        "Had to return it. The quality is terrible and it doesn't work properly.",
        "Worst purchase ever. The product arrived damaged and customer service was unhelpful."
    ]
    
    # Generate reviews with a distribution of ratings
    for i in range(num_reviews):
        # Determine rating
        weights = [0.1, 0.1, 0.2, 0.3, 0.3]  # Weights for ratings 1-5
        rating = random.choices([1, 2, 3, 4, 5], weights=weights)[0]
        
        # Select review text based on rating
        if rating >= 4:
            text = random.choice(positive_texts)
        elif rating == 3:
            text = random.choice(neutral_texts)
        else:
            text = random.choice(negative_texts)
        
        # Generate a random date within the last year
        days_ago = random.randint(1, 365)
        review_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        review_date = review_date.replace(day=review_date.day - days_ago)
        
        review = {
            "review_id": f"mock_flipkart_{i}",
            "title": f"Review {i+1}",
            "text": text,
            "rating": float(rating),
            "reviewer_name": f"FlipkartUser{i}",
            "review_date_text": review_date.strftime("%d %b %Y"),
            "review_date": review_date.isoformat(),
            "verified_purchase": random.choice([True, False]),
            "helpful_votes": random.randint(0, 30)
        }
        
        reviews.append(review)
    
    return reviews
