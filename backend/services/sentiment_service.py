import os
import json
import requests
from typing import Dict, Any, List
import logging
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Get API keys and configuration from environment variables
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
USE_LOCAL_LLM = os.getenv("USE_LOCAL_LLM", "false").lower() == "true"

# Try to import VADER for fallback sentiment analysis
try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    vader_analyzer = SentimentIntensityAnalyzer()
    vader_available = True
    logger.info("VADER sentiment analyzer loaded successfully")
except ImportError:
    vader_available = False
    logger.warning("VADER sentiment analyzer not available, will use basic fallback")

def analyze_sentiment(text: str) -> Dict[str, Any]:
    """
    Analyze the sentiment of a text using Gemini API or fallback methods.

    Args:
        text: The text to analyze

    Returns:
        Dictionary containing sentiment analysis results
    """
    # Try Gemini API if key is available
    if GEMINI_API_KEY:
        try:
            return analyze_sentiment_gemini(text)
        except Exception as e:
            logger.error(f"Error using Gemini API: {e}")
            # Fall back to VADER or basic analysis

    # Fall back to VADER if available
    if vader_available:
        return analyze_sentiment_vader(text)

    # Basic fallback if nothing else works
    return analyze_sentiment_basic(text)

def analyze_sentiment_gemini(text: str) -> Dict[str, Any]:
    """
    Analyze the sentiment of a text using Google's Gemini API.

    Args:
        text: The text to analyze

    Returns:
        Dictionary containing sentiment analysis results
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": GEMINI_API_KEY
    }

    prompt = f"""
    Analyze the sentiment of the following product review. Classify it as POSITIVE, NEUTRAL, or NEGATIVE.
    Also identify key aspects mentioned in the review and the sentiment towards each aspect.

    Review: {text}

    Provide your response in the following JSON format:
    {{
        "sentiment": "POSITIVE/NEUTRAL/NEGATIVE",
        "sentiment_score": 0.0 to 1.0,
        "aspects": {{
            "aspect1": {{"sentiment": "POSITIVE/NEUTRAL/NEGATIVE", "score": 0.0 to 1.0}},
            "aspect2": {{"sentiment": "POSITIVE/NEUTRAL/NEGATIVE", "score": 0.0 to 1.0}}
        }},
        "summary": "Brief summary of the review sentiment",
        "strengths": ["List of product strengths mentioned"],
        "weaknesses": ["List of product weaknesses mentioned"],
        "improvement_suggestions": ["Suggestions for improvement if any"]
    }}
    """

    data = {
        "contents": [{
            "parts": [{
                "text": prompt
            }]
        }]
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()

        response_data = response.json()

        # Extract text from response
        response_text = response_data["candidates"][0]["content"]["parts"][0]["text"]

        # Find JSON content (it might be wrapped in markdown code blocks)
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1

        if json_start >= 0 and json_end > json_start:
            json_str = response_text[json_start:json_end]
            result = json.loads(json_str)

            # Normalize the result to match our expected format
            normalized_result = {
                "sentiment": result["sentiment"].lower(),
                "score": result["sentiment_score"],
                "aspects": result.get("aspects", {}),
                "summary": result.get("summary", ""),
                "strengths": result.get("strengths", []),
                "weaknesses": result.get("weaknesses", []),
                "improvement_suggestions": result.get("improvement_suggestions", [])
            }

            return normalized_result
        else:
            logger.error("Failed to extract JSON from Gemini response")
            raise ValueError("Invalid response format from Gemini API")

    except Exception as e:
        logger.error(f"Error in Gemini API request: {e}")
        raise



def analyze_sentiment_vader(text: str) -> Dict[str, Any]:
    """
    Analyze the sentiment of a text using VADER.

    Args:
        text: The text to analyze

    Returns:
        Dictionary containing sentiment analysis results
    """
    try:
        # Get VADER scores
        scores = vader_analyzer.polarity_scores(text)
        compound = scores['compound']

        # Determine sentiment based on compound score
        if compound >= 0.05:
            sentiment = "positive"
        elif compound <= -0.05:
            sentiment = "negative"
        else:
            sentiment = "neutral"

        # Convert compound score to 0-1 range
        normalized_score = (compound + 1) / 2

        # Extract aspects (simple keyword-based approach)
        aspects = extract_aspects_basic(text, sentiment)

        return {
            "sentiment": sentiment,
            "score": normalized_score,
            "aspects": aspects,
            "summary": f"The review expresses {sentiment} sentiment overall.",
            "strengths": extract_strengths_weaknesses(text, True),
            "weaknesses": extract_strengths_weaknesses(text, False),
            "improvement_suggestions": []
        }
    except Exception as e:
        logger.error(f"Error in VADER analysis: {e}")
        return analyze_sentiment_basic(text)

def analyze_sentiment_basic(text: str) -> Dict[str, Any]:
    """
    Basic sentiment analysis using keyword matching.

    Args:
        text: The text to analyze

    Returns:
        Dictionary containing sentiment analysis results
    """
    text_lower = text.lower()

    # Simple keyword-based sentiment analysis
    positive_words = ["good", "great", "excellent", "amazing", "love", "best", "perfect", "recommend", "happy", "satisfied"]
    negative_words = ["bad", "poor", "terrible", "awful", "hate", "worst", "disappointed", "waste", "unhappy", "broken"]

    positive_count = sum(1 for word in positive_words if word in text_lower)
    negative_count = sum(1 for word in negative_words if word in text_lower)

    # Determine sentiment
    if positive_count > negative_count:
        sentiment = "positive"
        score = 0.5 + min(0.5, (positive_count - negative_count) / 10)
    elif negative_count > positive_count:
        sentiment = "negative"
        score = 0.5 - min(0.5, (negative_count - positive_count) / 10)
    else:
        sentiment = "neutral"
        score = 0.5

    # Extract aspects (simple keyword-based approach)
    aspects = extract_aspects_basic(text, sentiment)

    return {
        "sentiment": sentiment,
        "score": score,
        "aspects": aspects,
        "summary": f"The review expresses {sentiment} sentiment overall.",
        "strengths": extract_strengths_weaknesses(text, True),
        "weaknesses": extract_strengths_weaknesses(text, False),
        "improvement_suggestions": []
    }

def extract_aspects_basic(text: str, overall_sentiment: str) -> Dict[str, Dict[str, Any]]:
    """
    Extract aspects and their sentiment using a basic approach.

    Args:
        text: The review text
        overall_sentiment: The overall sentiment of the review

    Returns:
        Dictionary of aspects and their sentiment
    """
    text_lower = text.lower()
    aspects = {}

    # Common product aspects
    aspect_keywords = {
        "quality": ["quality", "build", "construction", "durability", "sturdy", "solid"],
        "price": ["price", "cost", "value", "expensive", "cheap", "affordable", "worth"],
        "performance": ["performance", "speed", "fast", "slow", "responsive", "lag"],
        "design": ["design", "look", "style", "appearance", "aesthetic", "beautiful", "ugly"],
        "usability": ["easy to use", "user friendly", "intuitive", "complicated", "difficult", "simple"],
        "customer service": ["service", "support", "help", "assistance", "representative", "warranty"],
        "delivery": ["delivery", "shipping", "arrived", "package", "box", "packaging"]
    }

    # Check for each aspect
    for aspect, keywords in aspect_keywords.items():
        if any(keyword in text_lower for keyword in keywords):
            # Simple sentiment assignment based on context
            sentiment = overall_sentiment
            score = 0.7 if sentiment == "positive" else (0.3 if sentiment == "negative" else 0.5)

            aspects[aspect] = {
                "sentiment": sentiment,
                "score": score
            }

    return aspects

def extract_strengths_weaknesses(text: str, strengths: bool = True) -> List[str]:
    """
    Extract strengths or weaknesses from text using a basic approach.

    Args:
        text: The review text
        strengths: If True, extract strengths, otherwise extract weaknesses

    Returns:
        List of strengths or weaknesses
    """
    sentences = text.split('.')
    results = []

    # Keywords that indicate strengths or weaknesses
    strength_indicators = ["good", "great", "excellent", "love", "best", "perfect", "recommend", "happy", "satisfied", "like"]
    weakness_indicators = ["bad", "poor", "terrible", "hate", "worst", "disappointed", "waste", "unhappy", "broken", "issue", "problem"]

    indicators = strength_indicators if strengths else weakness_indicators

    # Check each sentence for indicators
    for sentence in sentences:
        if any(indicator in sentence.lower() for indicator in indicators):
            clean_sentence = sentence.strip()
            if clean_sentence and len(clean_sentence) > 5:
                results.append(clean_sentence)

    return results[:3]  # Limit to top 3

def generate_actionable_insights(reviews: List[Dict[str, Any]], product_name: str) -> Dict[str, Any]:
    """
    Generate actionable insights from a collection of reviews.

    Args:
        reviews: List of review dictionaries with sentiment analysis
        product_name: Name of the product

    Returns:
        Dictionary containing actionable insights
    """
    if not reviews:
        return {
            "key_strengths": [],
            "key_weaknesses": [],
            "improvement_suggestions": [],
            "competitive_advantage": "Not enough data",
            "customer_satisfaction_summary": "Not enough data",
            "actionable_insights": []
        }

    # Use Gemini API if available
    if GEMINI_API_KEY:
        try:
            return generate_insights_gemini(reviews, product_name)
        except Exception as e:
            logger.error(f"Error generating insights with Gemini: {e}")

    # Fallback to basic insights generation
    return generate_insights_basic(reviews, product_name)

def generate_insights_gemini(reviews: List[Dict[str, Any]], product_name: str) -> Dict[str, Any]:
    """
    Generate actionable insights using Gemini API.

    Args:
        reviews: List of review dictionaries with sentiment analysis
        product_name: Name of the product

    Returns:
        Dictionary containing actionable insights
    """
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": GEMINI_API_KEY
    }

    # Prepare review summaries for the prompt
    review_summaries = []
    for i, review in enumerate(reviews[:20]):  # Limit to 20 reviews to avoid token limits
        sentiment = review.get("sentiment", "unknown")
        score = review.get("score", 0)
        text = review.get("text", "")
        rating = review.get("rating", None)

        rating_str = f", Rating: {rating}/5" if rating is not None else ""
        review_summaries.append(f"Review {i+1} (Sentiment: {sentiment}, Score: {score}{rating_str}): {text}")

    reviews_text = "\n".join(review_summaries)

    prompt = f"""
    You are a brand strategy expert. Analyze these reviews for {product_name} and provide actionable insights.

    REVIEWS:
    {reviews_text}

    Based on these reviews, provide a strategic analysis in the following JSON format:
    {{
        "key_strengths": ["List the top 3-5 strengths of the product based on positive reviews"],
        "key_weaknesses": ["List the top 3-5 weaknesses or issues mentioned in negative reviews"],
        "improvement_suggestions": ["Provide 3-5 specific, actionable suggestions to improve the product or service"],
        "competitive_advantage": "Identify the main competitive advantage this product has based on reviews",
        "customer_satisfaction_summary": "Summarize the overall customer satisfaction in 1-2 sentences",
        "actionable_insights": [
            {{
                "insight": "A specific insight about the product or customer perception",
                "action": "A specific action the company should take based on this insight",
                "priority": "high/medium/low",
                "impact_area": "product/marketing/customer service/etc."
            }},
            // 2-3 more actionable insights
        ]
    }}
    """

    data = {
        "contents": [{
            "parts": [{
                "text": prompt
            }]
        }]
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()

        response_data = response.json()

        # Extract text from response
        response_text = response_data["candidates"][0]["content"]["parts"][0]["text"]

        # Find JSON content
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1

        if json_start >= 0 and json_end > json_start:
            json_str = response_text[json_start:json_end]
            result = json.loads(json_str)
            return result
        else:
            logger.error("Failed to extract JSON from Gemini response")
            return generate_insights_basic(reviews, product_name)

    except Exception as e:
        logger.error(f"Error in Gemini API request for insights: {e}")
        return generate_insights_basic(reviews, product_name)

def generate_insights_basic(reviews: List[Dict[str, Any]], product_name: str) -> Dict[str, Any]:
    """
    Generate basic actionable insights from reviews.

    Args:
        reviews: List of review dictionaries with sentiment analysis
        product_name: Name of the product

    Returns:
        Dictionary containing actionable insights
    """
    # Count sentiments
    sentiment_counts = {"positive": 0, "neutral": 0, "negative": 0}
    for review in reviews:
        sentiment = review.get("sentiment", "neutral")
        sentiment_counts[sentiment] = sentiment_counts.get(sentiment, 0) + 1

    total_reviews = len(reviews)
    positive_percentage = (sentiment_counts.get("positive", 0) / total_reviews) * 100 if total_reviews > 0 else 0

    # Collect strengths and weaknesses
    all_strengths = []
    all_weaknesses = []

    for review in reviews:
        strengths = review.get("strengths", [])
        weaknesses = review.get("weaknesses", [])
        all_strengths.extend(strengths)
        all_weaknesses.extend(weaknesses)

    # Get most common strengths and weaknesses
    key_strengths = list(set(all_strengths))[:5]
    key_weaknesses = list(set(all_weaknesses))[:5]

    # Generate improvement suggestions
    improvement_suggestions = []
    if key_weaknesses:
        for weakness in key_weaknesses[:3]:
            improvement_suggestions.append(f"Address issue: {weakness}")

    # Generate customer satisfaction summary
    if positive_percentage >= 70:
        satisfaction = "Customers are generally very satisfied with the product."
    elif positive_percentage >= 50:
        satisfaction = "Customers are moderately satisfied, but there are some areas for improvement."
    else:
        satisfaction = "Customer satisfaction is low. Immediate attention to product issues is recommended."

    # Generate actionable insights
    actionable_insights = [
        {
            "insight": "Customer sentiment analysis",
            "action": f"Focus on {'maintaining positive aspects' if positive_percentage >= 50 else 'addressing negative feedback'}",
            "priority": "high" if positive_percentage < 50 else "medium",
            "impact_area": "product"
        }
    ]

    if key_strengths:
        actionable_insights.append({
            "insight": f"Key strength: {key_strengths[0]}",
            "action": "Highlight this strength in marketing materials",
            "priority": "medium",
            "impact_area": "marketing"
        })

    if key_weaknesses:
        actionable_insights.append({
            "insight": f"Key weakness: {key_weaknesses[0]}",
            "action": "Develop improvement plan to address this issue",
            "priority": "high",
            "impact_area": "product development"
        })

    return {
        "key_strengths": key_strengths,
        "key_weaknesses": key_weaknesses,
        "improvement_suggestions": improvement_suggestions,
        "competitive_advantage": key_strengths[0] if key_strengths else "Not identified",
        "customer_satisfaction_summary": satisfaction,
        "actionable_insights": actionable_insights
    }
