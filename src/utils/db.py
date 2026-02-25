import os
import sqlite3
import pandas as pd
from sqlalchemy import create_engine

# Base directory of the project
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, 'data')

# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)

DB_PATH = os.path.join(DATA_DIR, 'housing_data.db')

def get_engine():
    """Returns a SQLAlchemy engine for the SQLite database."""
    return create_engine(f'sqlite:///{DB_PATH}')

def get_connection():
    """Returns a raw SQLite connection."""
    return sqlite3.connect(DB_PATH)

def init_db():
    print(f"Initializing database at {DB_PATH}...")
    pass

if __name__ == "__main__":
    init_db()
