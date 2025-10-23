from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from .database import Base

class SentimentEnum(enum.Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"

class Platform(enum.Enum):
    AMAZON = "amazon"
    FLIPKART = "flipkart"
    TWITTER = "twitter"
    REDDIT = "reddit"
    CUSTOM = "custom"

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    brand = Column(String(255))
    url = Column(String(500))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    reviews = relationship("Review", back_populates="product")
    insights = relationship("ActionableInsight", back_populates="product")

class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    platform = Column(Enum(Platform), nullable=False)
    rating = Column(Float)
    text = Column(Text)
    reviewer_name = Column(String(255))
    review_date = Column(DateTime)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Sentiment analysis results
    sentiment = Column(Enum(SentimentEnum))
    sentiment_score = Column(Float)
    
    # Relationships
    product = relationship("Product", back_populates="reviews")
    insights = relationship("ReviewInsight", back_populates="review")

class ReviewInsight(Base):
    __tablename__ = "review_insights"

    id = Column(Integer, primary_key=True, index=True)
    review_id = Column(Integer, ForeignKey("reviews.id"))
    aspect = Column(String(100))
    sentiment = Column(Enum(SentimentEnum))
    sentiment_score = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    review = relationship("Review", back_populates="insights")

class ActionableInsight(Base):
    __tablename__ = "actionable_insights"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    insight_text = Column(Text)
    category = Column(String(100))  # strength, weakness, opportunity, threat
    priority = Column(Integer)  # 1-5 scale
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    product = relationship("Product", back_populates="insights")

class SentimentSummary(Base):
    __tablename__ = "sentiment_summaries"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    platform = Column(Enum(Platform))
    positive_count = Column(Integer, default=0)
    neutral_count = Column(Integer, default=0)
    negative_count = Column(Integer, default=0)
    average_rating = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class ScrapingJob(Base):
    __tablename__ = "scraping_jobs"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    platform = Column(Enum(Platform))
    status = Column(String(50))  # pending, running, completed, failed
    reviews_scraped = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
    error_message = Column(Text)
