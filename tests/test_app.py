import unittest
import sys
import os
import json

# Add the parent directory to the path so we can import the app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app

class TestApp(unittest.TestCase):

    def setUp(self):
        """Set up test client"""
        self.app = app.test_client()
        self.app.testing = True

    def test_home_page(self):
        """Test that home page loads"""
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)

    def test_api_health(self):
        """Test the health check endpoint"""
        response = self.app.get('/api/health')
        self.assertEqual(response.status_code, 200)
        result = json.loads(response.data)
        self.assertEqual(result['status'], 'healthy')

if __name__ == '__main__':
    unittest.main()
