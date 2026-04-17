import sys
import os

# Add parent directory to path to import model.py
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from model import app

# Export the Flask app for Vercel
app = app
