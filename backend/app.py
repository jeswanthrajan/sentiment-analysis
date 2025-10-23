import os
import uuid
import json
import pandas as pd
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from flask import Flask, request, jsonify, render_template, redirect, url_for, flash, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Import services
from services.sentiment_service import analyze_sentiment, generate_actionable_insights
from services.scraper_service import (
    scrape_amazon_reviews_api, 
    scrape_flipkart_reviews, 
    extract_asin_from_url
)

# Import database models
from models.database import engine, get_db, Base
from models import models

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("sentimentscope.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload size

# Create uploads directory if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize Flask app
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH
app.secret_key = os.getenv('SECRET_KEY', 'sentimentscope-secret-key')
CORS(app)

# Create database tables
Base.metadata.create_all(bind=engine)

# Helper functions
def allowed_file(filename):
    """Check if file has an allowed extension"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def process_file(file) -> Tuple[Dict[str, Any], Optional[str]]:
    """
    Process uploaded file and return analysis results
    
    Args:
        file: Uploaded file object
        
    Returns:
        Tuple of (summary dict, error message or None)
    """
    try:
        # Save the file
        filename = secure_filename(file.filename)
        file_id = str(uuid.uuid4())
        file_dir = os.path.join(app.config['UPLOAD_FOLDER'], file_id)
        os.makedirs(file_dir, exist_ok=True)
        file_path = os.path.join(file_dir, filename)
        file.save(file_path)
        
        logger.info(f"File saved: {file_path}")
        
        # Determine file type and read accordingly
        file_ext = os.path.splitext(file_path)[1].lower()
        
        try:
            if file_ext == '.csv':
                df = pd.read_csv(file_path)
                logger.info(f"CSV file read successfully. Shape: {df.shape}")
            elif file_ext in ['.xlsx', '.xls']:
                df = pd.read_excel(file_path)
                logger.info(f"Excel file read successfully. Shape: {df.shape}")
            else:
                logger.error(f"Unsupported file format: {file_ext}")
                return None, f"Unsupported file format: {file_ext}. Please use CSV or Excel."
        except Exception as e:
            logger.error(f"Error reading file: {e}")
            return None, f"Error reading file: {str(e)}"
        
        # Log column names for debugging
        logger.info(f"Columns in file: {list(df.columns)}")
        
        # Determine file format (Amazon, custom, etc.)
        file_format = 'custom'
        
        # Check if it's an Amazon format
        amazon_columns = ['product_id', 'product_name', 'review_id', 'review_title', 'review_text', 'rating', 'review_date']
        if all(col in df.columns for col in ['product_name', 'review_text', 'rating']):
            file_format = 'amazon'
            logger.info("Detected Amazon format")
            
            # Prepare Amazon format
            if 'review_text' in df.columns and 'text' not in df.columns:
                df['text'] = df['review_text']
        
        # Find text column if not already identified
        text_column = None
        if 'text' in df.columns:
            text_column = 'text'
        elif 'review_text' in df.columns:
            text_column = 'review_text'
        elif 'comment' in df.columns:
            text_column = 'comment'
        elif 'feedback' in df.columns:
            text_column = 'feedback'
        else:
            # Use the first string column that has more than 10 characters on average
            for col in df.columns:
                if df[col].dtype == 'object':
                    if df[col].astype(str).str.len().mean() > 10:
                        text_column = col
                        logger.info(f"Using column '{col}' as text column")
                        break
        
        if not text_column:
            logger.error("No suitable text column found")
            return None, "No suitable text column found in the file. Please ensure there's a column with review text."
        
        # Find rating column if available
        rating_column = None
        if 'rating' in df.columns:
            rating_column = 'rating'
        elif 'stars' in df.columns:
            rating_column = 'stars'
        elif 'score' in df.columns:
            rating_column = 'score'
        
        # Process each row for sentiment analysis
        results = []
        mentions = []
        
        for idx, row in df.iterrows():
            text = str(row[text_column])
            
            # Skip empty or very short texts
            if len(text.strip()) < 5:
                continue
            
            # Analyze sentiment
            sentiment_result = analyze_sentiment(text)
            
            # Create result object
            result = {
                'text': text,
                'sentiment': sentiment_result['sentiment'],
                'score': sentiment_result['score'],
                'confidence': sentiment_result.get('confidence', 0.8),
                'aspects': sentiment_result.get('aspects', {}),
                'strengths': sentiment_result.get('strengths', []),
                'weaknesses': sentiment_result.get('weaknesses', []),
                'actionable_steps': '\n'.join(sentiment_result.get('improvement_suggestions', []))
            }
            
            # Add rating if available
            if rating_column and rating_column in row:
                try:
                    result['rating'] = float(row[rating_column])
                except (ValueError, TypeError):
                    pass
            
            # Add product name if available
            if 'product' in row:
                result['product'] = row['product']
            elif 'product_name' in row:
                result['product'] = row['product_name']
            
            # Add date if available
            if 'date' in row:
                result['date'] = row['date']
            elif 'review_date' in row:
                result['date'] = row['review_date']
            
            results.append(result)
            
            # Create mention object for visualization
            mention = {
                'source': 'uploaded_file',
                'type': 'review',
                'text': text,
                'sentiment': sentiment_result['sentiment'],
                'sentiment_score': sentiment_result['score']
            }
            
            # Add additional fields if available
            if 'product' in result:
                mention['product'] = result['product']
            if 'rating' in result:
                mention['rating'] = result['rating']
            if 'date' in result:
                mention['date'] = result['date']
            
            mentions.append(mention)
        
        # Calculate summary statistics
        total_reviews = len(results)
        positive_count = sum(1 for r in results if r['sentiment'] == 'positive')
        neutral_count = sum(1 for r in results if r['sentiment'] == 'neutral')
        negative_count = sum(1 for r in results if r['sentiment'] == 'negative')
        
        average_score = sum(r['score'] for r in results) / total_reviews if total_reviews > 0 else 0
        
        # Generate actionable insights
        insights = generate_actionable_insights(results, filename)
        
        # Save results to CSV
        results_df = pd.DataFrame(results)
        results_path = os.path.join(file_dir, 'results.csv')
        results_df.to_csv(results_path, index=False)
        
        # Save mentions to JSON
        mentions_path = os.path.join(file_dir, 'mentions.json')
        with open(mentions_path, 'w') as f:
            json.dump(mentions, f)
        
        # Save summary to JSON
        summary = {
            'total_reviews': total_reviews,
            'sentiment_distribution': {
                'positive': positive_count,
                'neutral': neutral_count,
                'negative': negative_count
            },
            'average_score': average_score,
            'file_id': file_id,
            'filename': filename,
            'file_format': file_format,
            'is_amazon_format': file_format == 'amazon',
            'has_mentions': len(mentions) > 0,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'insights': insights
        }
        
        summary_path = os.path.join(file_dir, 'summary.json')
        with open(summary_path, 'w') as f:
            json.dump(summary, f)
        
        logger.info(f"File processing complete. Results saved to {file_dir}")
        return summary, None
        
    except Exception as e:
        logger.error(f"Error processing file: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None, f"Error processing file: {str(e)}"

# Routes
@app.route('/')
def index():
    """Home page"""
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    """Dashboard page"""
    return render_template('dashboard.html')

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    """File upload page"""
    if request.method == 'POST':
        # Check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        
        file = request.files['file']
        
        # If user does not select file, browser also submits an empty part without filename
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            try:
                # Process the file
                summary, error = process_file(file)
                
                if error:
                    flash(error)
                    return redirect(request.url)
                
                # Get the results for display
                file_id = summary['file_id']
                filename = summary['filename']
                
                # Read the results file
                results_path = os.path.join(app.config['UPLOAD_FOLDER'], file_id, 'results.csv')
                results_df = pd.read_csv(results_path)
                results = results_df.to_dict('records')
                
                # Update the recent uploads table in the dashboard
                return render_template('results.html', results=results, summary=summary, file_id=file_id, filename=filename)
                
            except Exception as e:
                logger.error(f"Error processing file: {e}")
                flash(f"Error processing file: {str(e)}")
                return redirect(request.url)
        else:
            flash(f"Invalid file format. Supported formats: {', '.join(ALLOWED_EXTENSIONS)}")
            return redirect(request.url)
    
    return render_template('upload.html')

@app.route('/api/analyze', methods=['POST'])
def analyze_text():
    """API endpoint for analyzing text"""
    data = request.json
    text = data.get('text', '')
    
    if not text:
        return jsonify({'error': 'No text provided'}), 400
    
    # Analyze sentiment
    sentiment_result = analyze_sentiment(text)
    
    return jsonify(sentiment_result)

@app.route('/api/upload', methods=['POST'])
def api_upload_file():
    """API endpoint for file upload and analysis"""
    # Check if the post request has the file part
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    
    # If user does not select file, browser also submits an empty part without filename
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file and allowed_file(file.filename):
        # Process the file
        summary, error = process_file(file)
        
        if error:
            return jsonify({'error': error}), 500
        
        return jsonify(summary)
    
    return jsonify({'error': f"Invalid file format. Supported formats: {', '.join(ALLOWED_EXTENSIONS)}"}), 400

@app.route('/api/scrape', methods=['POST'])
def scrape_reviews():
    """API endpoint for scraping reviews"""
    data = request.json
    url = data.get('url', '')
    platform = data.get('platform', 'amazon')
    num_reviews = int(data.get('num_reviews', 20))
    rapidapi_key = data.get('rapidapi_key', None)
    
    if not url:
        return jsonify({'error': 'No URL provided'}), 400
    
    try:
        # Create database session
        Session = sessionmaker(bind=engine)
        db = Session()
        
        # Scrape reviews based on platform
        if platform.lower() == 'amazon':
            # Extract ASIN from URL
            asin = extract_asin_from_url(url)
            if not asin:
                return jsonify({'error': 'Could not extract ASIN from URL'}), 400
            
            # Scrape Amazon reviews
            product_info, reviews = scrape_amazon_reviews_api(asin, num_reviews, rapidapi_key)
            
            # Create or get product
            product = db.query(models.Product).filter_by(name=product_info['name']).first()
            if not product:
                product = models.Product(
                    name=product_info['name'],
                    brand=product_info.get('brand', 'Unknown'),
                    url=product_info['url']
                )
                db.add(product)
                db.commit()
                db.refresh(product)
            
            # Process reviews
            reviews_added = 0
            for review_data in reviews:
                # Check if review already exists
                existing_review = db.query(models.Review).filter_by(
                    product_id=product.id,
                    platform=models.Platform.AMAZON,
                    text=review_data['text']
                ).first()
                
                if not existing_review:
                    # Analyze sentiment
                    sentiment_result = analyze_sentiment(review_data['text'])
                    
                    # Create review
                    review = models.Review(
                        product_id=product.id,
                        platform=models.Platform.AMAZON,
                        rating=review_data.get('rating', None),
                        text=review_data['text'],
                        reviewer_name=review_data.get('reviewer_name', 'Anonymous'),
                        review_date=datetime.fromisoformat(review_data['review_date']) if 'review_date' in review_data else datetime.now(),
                        sentiment=models.SentimentEnum[sentiment_result['sentiment'].upper()],
                        sentiment_score=sentiment_result['score']
                    )
                    db.add(review)
                    reviews_added += 1
                    
                    # Add aspects as insights
                    for aspect, data in sentiment_result.get('aspects', {}).items():
                        insight = models.ReviewInsight(
                            review=review,
                            aspect=aspect,
                            sentiment=models.SentimentEnum[data['sentiment'].upper()],
                            sentiment_score=data['score']
                        )
                        db.add(insight)
            
            db.commit()
            
            return jsonify({
                'success': True,
                'product_id': product.id,
                'product_name': product.name,
                'reviews_scraped': reviews_added,
                'message': f"Successfully scraped {reviews_added} new reviews for {product.name}"
            })
            
        elif platform.lower() == 'flipkart':
            # Scrape Flipkart reviews
            product_info, reviews = scrape_flipkart_reviews(url, num_reviews)
            
            # Create or get product
            product = db.query(models.Product).filter_by(name=product_info['name']).first()
            if not product:
                product = models.Product(
                    name=product_info['name'],
                    url=product_info['url']
                )
                db.add(product)
                db.commit()
                db.refresh(product)
            
            # Process reviews
            reviews_added = 0
            for review_data in reviews:
                # Check if review already exists
                existing_review = db.query(models.Review).filter_by(
                    product_id=product.id,
                    platform=models.Platform.FLIPKART,
                    text=review_data['text']
                ).first()
                
                if not existing_review:
                    # Analyze sentiment
                    sentiment_result = analyze_sentiment(review_data['text'])
                    
                    # Create review
                    review = models.Review(
                        product_id=product.id,
                        platform=models.Platform.FLIPKART,
                        rating=review_data.get('rating', None),
                        text=review_data['text'],
                        reviewer_name=review_data.get('reviewer_name', 'Anonymous'),
                        review_date=datetime.fromisoformat(review_data['review_date']) if 'review_date' in review_data else datetime.now(),
                        sentiment=models.SentimentEnum[sentiment_result['sentiment'].upper()],
                        sentiment_score=sentiment_result['score']
                    )
                    db.add(review)
                    reviews_added += 1
                    
                    # Add aspects as insights
                    for aspect, data in sentiment_result.get('aspects', {}).items():
                        insight = models.ReviewInsight(
                            review=review,
                            aspect=aspect,
                            sentiment=models.SentimentEnum[data['sentiment'].upper()],
                            sentiment_score=data['score']
                        )
                        db.add(insight)
            
            db.commit()
            
            return jsonify({
                'success': True,
                'product_id': product.id,
                'product_name': product.name,
                'reviews_scraped': reviews_added,
                'message': f"Successfully scraped {reviews_added} new reviews for {product.name}"
            })
        
        else:
            return jsonify({'error': f"Unsupported platform: {platform}"}), 400
            
    except Exception as e:
        logger.error(f"Error scraping reviews: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'error': f"Error scraping reviews: {str(e)}"}), 500

@app.route('/api/products', methods=['GET'])
def get_products():
    """API endpoint for getting products"""
    try:
        # Create database session
        Session = sessionmaker(bind=engine)
        db = Session()
        
        # Get products
        products = db.query(models.Product).all()
        
        # Convert to dict
        products_list = []
        for product in products:
            products_list.append({
                'id': product.id,
                'name': product.name,
                'brand': product.brand,
                'url': product.url,
                'created_at': product.created_at.isoformat() if product.created_at else None
            })
        
        return jsonify(products_list)
        
    except Exception as e:
        logger.error(f"Error getting products: {e}")
        return jsonify({'error': f"Error getting products: {str(e)}"}), 500

@app.route('/api/products/<int:product_id>/reviews', methods=['GET'])
def get_product_reviews(product_id):
    """API endpoint for getting product reviews"""
    try:
        # Create database session
        Session = sessionmaker(bind=engine)
        db = Session()
        
        # Get product
        product = db.query(models.Product).filter_by(id=product_id).first()
        if not product:
            return jsonify({'error': 'Product not found'}), 404
        
        # Get reviews
        reviews = db.query(models.Review).filter_by(product_id=product_id).all()
        
        # Convert to dict
        reviews_list = []
        for review in reviews:
            reviews_list.append({
                'id': review.id,
                'product_id': review.product_id,
                'platform': review.platform.value,
                'rating': review.rating,
                'text': review.text,
                'reviewer_name': review.reviewer_name,
                'review_date': review.review_date.isoformat() if review.review_date else None,
                'sentiment': review.sentiment.value,
                'sentiment_score': review.sentiment_score,
                'created_at': review.created_at.isoformat() if review.created_at else None
            })
        
        return jsonify(reviews_list)
        
    except Exception as e:
        logger.error(f"Error getting product reviews: {e}")
        return jsonify({'error': f"Error getting product reviews: {str(e)}"}), 500

@app.route('/api/products/<int:product_id>/insights', methods=['GET'])
def get_product_insights(product_id):
    """API endpoint for getting product insights"""
    try:
        # Create database session
        Session = sessionmaker(bind=engine)
        db = Session()
        
        # Get product
        product = db.query(models.Product).filter_by(id=product_id).first()
        if not product:
            return jsonify({'error': 'Product not found'}), 404
        
        # Get reviews
        reviews = db.query(models.Review).filter_by(product_id=product_id).all()
        
        # Convert to format for insights generation
        reviews_list = []
        for review in reviews:
            reviews_list.append({
                'text': review.text,
                'sentiment': review.sentiment.value,
                'score': review.sentiment_score,
                'rating': review.rating
            })
        
        # Generate insights
        insights = generate_actionable_insights(reviews_list, product.name)
        
        return jsonify(insights)
        
    except Exception as e:
        logger.error(f"Error getting product insights: {e}")
        return jsonify({'error': f"Error getting product insights: {str(e)}"}), 500

@app.route('/download/<file_id>')
def download_results(file_id):
    """Download the results file"""
    try:
        results_file = os.path.join(app.config['UPLOAD_FOLDER'], file_id, 'results.csv')
        return send_file(results_file, as_attachment=True, download_name='sentiment_analysis_results.csv')
    except Exception as e:
        logger.error(f"Error downloading results: {e}")
        flash(f"Error downloading results: {str(e)}")
        return redirect(url_for('upload_file'))

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
