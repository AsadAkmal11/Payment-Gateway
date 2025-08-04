#!/usr/bin/env python3
"""
Database Reset Script for Payment Gateway
This script will drop and recreate all tables with the new schema.
"""

import sys
import os

# Add the app directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import Base, engine
from app.model import Transaction

def reset_database():
    """Drop and recreate all database tables"""
    try:
        print("🗑️  Dropping existing tables...")
        Base.metadata.drop_all(bind=engine)
        print("✅ Tables dropped successfully")
        
        print("🏗️  Creating new tables...")
        Base.metadata.create_all(bind=engine)
        print("✅ Tables created successfully")
        
        print("🎉 Database reset completed!")
        print("📋 New table structure:")
        print("   - id (Primary Key)")
        print("   - full_name (VARCHAR)")
        print("   - email (VARCHAR)")
        print("   - phone (VARCHAR)")
        print("   - amount (FLOAT)")
        print("   - reference (VARCHAR, Unique)")
        print("   - status (VARCHAR)")
        print("   - created_at (TIMESTAMP)")
        
    except Exception as e:
        print(f"❌ Error resetting database: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    print("🚀 Payment Gateway Database Reset")
    print("=" * 40)
    
    # Ask for confirmation
    response = input("⚠️  This will DELETE ALL DATA. Are you sure? (yes/no): ")
    
    if response.lower() in ['yes', 'y']:
        reset_database()
    else:
        print("❌ Database reset cancelled.")
        sys.exit(0) 