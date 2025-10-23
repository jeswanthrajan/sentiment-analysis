import os
import sys
from dotenv import load_dotenv

# Add the backend directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

# Import database models
from backend.models.database import Base, engine
from backend.models import models

# Load environment variables
load_dotenv()

def init_db():
    """Initialize the database by creating all tables"""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")

if __name__ == "__main__":
    init_db()
