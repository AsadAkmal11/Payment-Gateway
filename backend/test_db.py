#!/usr/bin/env python3
"""
Database Connection Test Script
This script tests the database connection and creates tables if needed.
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, ProgrammingError

def test_database_connection():
    print("🔍 Testing Database Connection...")
    
    # Check if .env file exists
    env_file = os.path.join(os.path.dirname(__file__), '.env')
    if not os.path.exists(env_file):
        print("❌ No .env file found!")
        print("📝 Please create a .env file with the following content:")
        print("""
# Database Configuration
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_HOST=localhost
DB_NAME=payment_gateway

# Server Configuration
HOST=0.0.0.0
PORT=8000

# Security Configuration
HMAC_SECRET=your_hmac_secret_key_here
SECURITY_SALT=your_security_salt_here
ENFORCE_HTTPS=false

# Stripe Configuration
STRIPE_SECRET_KEY=sk_test_your_stripe_key_here
        """)
        return False
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Get database configuration
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")
    db_host = os.getenv("DB_HOST")
    db_name = os.getenv("DB_NAME")
    
    print(f"📊 Database Config:")
    print(f"   User: {db_user}")
    print(f"   Host: {db_host}")
    print(f"   Database: {db_name}")
    print(f"   Password: {'*' * len(db_password) if db_password else 'None'}")
    
    if not all([db_user, db_host, db_name]):
        print("❌ Missing required database configuration!")
        return False
    
    # Test connection
    try:
        # First try to connect to MySQL server
        server_url = f"mysql+pymysql://{db_user}:{db_password}@{db_host}"
        engine = create_engine(server_url)
        
        with engine.connect() as conn:
            result = conn.execute(text("SELECT VERSION()"))
            version = result.fetchone()[0]
            print(f"✅ Connected to MySQL Server: {version}")
        
        # Now try to connect to specific database
        db_url = f"mysql+pymysql://{db_user}:{db_password}@{db_host}/{db_name}"
        engine = create_engine(db_url)
        
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print(f"✅ Connected to database '{db_name}' successfully!")
            
            # Check if tables exist
            result = conn.execute(text("SHOW TABLES"))
            tables = [row[0] for row in result.fetchall()]
            print(f"📋 Existing tables: {tables}")
            
            if not tables:
                print("⚠️  No tables found. The backend will create them on startup.")
            else:
                print("✅ Tables exist in database.")
        
        return True
        
    except OperationalError as e:
        print(f"❌ Database connection failed: {e}")
        print("\n💡 Troubleshooting tips:")
        print("1. Make sure MySQL is running")
        print("2. Check your MySQL password in .env file")
        print("3. Make sure the database 'payment_gateway' exists")
        print("4. Try creating the database manually:")
        print("   mysql -u root -p")
        print("   CREATE DATABASE payment_gateway;")
        return False
        
    except ProgrammingError as e:
        print(f"❌ Database error: {e}")
        return False
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = test_database_connection()
    if success:
        print("\n🎉 Database connection test passed!")
        print("🚀 You can now start the backend server.")
    else:
        print("\n❌ Database connection test failed!")
        print("Please fix the issues above before starting the backend.")
        sys.exit(1) 