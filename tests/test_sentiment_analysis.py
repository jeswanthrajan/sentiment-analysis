import unittest
import sys
import os

# Add the parent directory to the path so we can import the app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.sentiment_service import analyze_sentiment

class TestSentimentAnalysis(unittest.TestCase):
    
    def test_positive_sentiment(self):
        """Test that positive text returns positive sentiment"""
        text = "I absolutely love this product! It's amazing and works perfectly."
        result = analyze_sentiment(text)
        self.assertEqual(result['sentiment'], 'positive')
        self.assertGreater(result['score'], 0.5)
    
    def test_negative_sentiment(self):
        """Test that negative text returns negative sentiment"""
        text = "This is terrible. I hate it and it doesn't work at all."
        result = analyze_sentiment(text)
        self.assertEqual(result['sentiment'], 'negative')
        self.assertLess(result['score'], 0.5)
    
    def test_neutral_sentiment(self):
        """Test that neutral text returns neutral sentiment"""
        text = "This product is okay. It works as expected."
        result = analyze_sentiment(text)
        self.assertEqual(result['sentiment'], 'neutral')
        self.assertGreaterEqual(result['score'], 0.3)
        self.assertLessEqual(result['score'], 0.7)

if __name__ == '__main__':
    unittest.main()
