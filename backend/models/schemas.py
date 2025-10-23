from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from enum import Enum

# Enums
class SentimentEnum(str, Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"

class PlatformEnum(str, Enum):
    AMAZON = "amazon"
    FLIPKART = "flipkart"
    TWITTER = "twitter"
    REDDIT = "reddit"
    CUSTOM = "custom"

# Base schemas
class ProductBase(BaseModel):
    name: str
    brand: Optional[str] = None
    url: Optional[str] = None

class ReviewBase(BaseModel):
    product_id: int
    platform: PlatformEnum
    rating: Optional[float] = None
    text: str
    reviewer_name: Optional[str] = None
    review_date: Optional[datetime] = None

class InsightBase(BaseModel):
    review_id: int
    aspect: str
    sentiment: SentimentEnum
    sentiment_score: float

class ActionableInsightBase(BaseModel):
    product_id: int
    insight_text: str
    category: str
    priority: int = Field(ge=1, le=5)

# Create schemas
class ProductCreate(ProductBase):
    pass

class ReviewCreate(ReviewBase):
    pass

class InsightCreate(InsightBase):
    pass

class ActionableInsightCreate(ActionableInsightBase):
    pass

# Response schemas
class Product(ProductBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True

class Review(ReviewBase):
    id: int
    sentiment: Optional[SentimentEnum] = None
    sentiment_score: Optional[float] = None
    created_at: datetime

    class Config:
        orm_mode = True

class ReviewWithInsights(Review):
    insights: List["Insight"] = []

    class Config:
        orm_mode = True

class Insight(InsightBase):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True

class ActionableInsight(ActionableInsightBase):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True

class SentimentSummary(BaseModel):
    product_id: int
    platform: Optional[PlatformEnum] = None
    positive_count: int
    neutral_count: int
    negative_count: int
    average_rating: Optional[float] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True

# Scraping schemas
class ScrapingRequest(BaseModel):
    product_url: str
    platform: PlatformEnum
    num_reviews: Optional[int] = 20
    rapidapi_key: Optional[str] = None

class ScrapingResponse(BaseModel):
    product_id: int
    product_name: str
    reviews_scraped: int
    success: bool
    message: str

# Sentiment Analysis schemas
class SentimentAnalysisRequest(BaseModel):
    text: str

class SentimentAnalysisResponse(BaseModel):
    sentiment: SentimentEnum
    sentiment_score: float
    aspects: Optional[Dict[str, Dict[str, Any]]] = None

# File Upload schemas
class FileUploadResponse(BaseModel):
    file_id: str
    filename: str
    total_reviews: int
    sentiment_distribution: Dict[str, int]
    average_score: float

# Dashboard schemas
class DashboardStats(BaseModel):
    total_reviews: int
    average_rating: float
    sentiment_distribution: Dict[str, int]
    platform_distribution: Dict[str, int]
    recent_reviews: List[Review]
    top_insights: List[ActionableInsight]

# Update forward references
ReviewWithInsights.update_forward_refs()
