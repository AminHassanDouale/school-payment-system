"""
Database Initialization Script

This script initializes the database and creates the first API token for the Scolapp system.
Run this after setting up the database to create initial data.

Usage:
    python init_db.py
"""

import sys
import os
from datetime import datetime, timedelta
from passlib.context import CryptContext
import secrets

# Add project root to path so `app` package is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import Base, engine, SessionLocal
from app.models.models import APIToken
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def generate_api_credentials():
    """Generate secure API key and secret"""
    api_key = f"sk_{secrets.token_urlsafe(32)}"
    api_secret = secrets.token_urlsafe(48)
    return api_key, api_secret


def init_database():
    """Initialize database - create all tables"""
    print("=" * 60)
    print("School Payment System - Database Initialization")
    print("=" * 60)
    print()
    
    try:
        # Create all tables
        print("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        print("✓ Tables created successfully")
        print()
        
        # Create session
        db = SessionLocal()
        
        # Check if API token already exists
        existing_token = db.query(APIToken).filter(APIToken.name == "Scolapp Main System").first()
        
        if existing_token:
            print("⚠ Warning: API token for 'Scolapp Main System' already exists")
            print(f"  Created at: {existing_token.created_at}")
            print()
            print("To create a new token, delete the existing one first or use a different name.")
            db.close()
            return
        
        # Generate API credentials
        print("Generating API credentials for Scolapp system...")
        api_key, api_secret = generate_api_credentials()
        api_secret_hash = pwd_context.hash(api_secret)
        
        # Create API token
        token = APIToken(
            name="Scolapp Main System",
            api_key=api_key,
            api_secret_hash=api_secret_hash,
            is_active=True,
            created_at=datetime.utcnow(),
            expires_at=None  # No expiration
        )
        
        db.add(token)
        db.commit()
        db.refresh(token)
        
        print("✓ API Token created successfully")
        print()
        print("=" * 60)
        print("IMPORTANT: Save these credentials securely!")
        print("=" * 60)
        print()
        print(f"Token Name:   {token.name}")
        print(f"API Key:      {api_key}")
        print(f"API Secret:   {api_secret}")
        print(f"Created At:   {token.created_at}")
        print()
        print("⚠ SECURITY WARNING:")
        print("  - Store these credentials in a secure location")
        print("  - Add them to your .env file on the Scolapp server")
        print("  - Never commit these to version control")
        print("  - This API secret will NOT be shown again")
        print()
        print("=" * 60)
        print()
        
        # Create .env entry example
        print("Add these to your Scolapp .env file:")
        print()
        print(f"PAYMENT_API_KEY={api_key}")
        print(f"PAYMENT_API_SECRET={api_secret}")
        print(f"PAYMENT_API_URL=https://api.scolapp.com/api/v1")
        print()
        print("=" * 60)
        
        db.close()
        
    except Exception as e:
        print(f"✗ Error initializing database: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def create_test_invoice():
    """Create a test invoice for verification (optional)"""
    from app.models.models import Invoice, FeeType, InvoiceStatus
    
    db = SessionLocal()
    
    try:
        # Check if test invoice exists
        existing = db.query(Invoice).filter(Invoice.order_id == "TEST-001").first()
        if existing:
            print("Test invoice already exists")
            return
        
        # Get the API token
        token = db.query(APIToken).filter(APIToken.name == "Scolapp Main System").first()
        if not token:
            print("Error: API token not found. Run init_database() first.")
            return
        
        # Create test invoice
        test_invoice = Invoice(
            order_id="TEST-001",
            student_id="STU-TEST-001",
            student_name="Test Student",
            guardian_phone="+25361234567",
            guardian_email="test@scolapp.com",
            fee_type=FeeType.TUITION,
            amount=1000.00,
            currency="DJF",
            due_date=datetime.utcnow() + timedelta(days=30),
            description="Test invoice for system verification",
            status=InvoiceStatus.PENDING,
            payment_link=f"{settings.SCOLAPP_DOMAIN}/pay/TEST-001",
            created_by_token_id=token.id
        )
        
        db.add(test_invoice)
        db.commit()
        
        print()
        print("✓ Test invoice created successfully")
        print(f"  Order ID: {test_invoice.order_id}")
        print(f"  Amount: {test_invoice.amount} DJF")
        print()
        
    except Exception as e:
        print(f"Error creating test invoice: {str(e)}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    print()
    init_database()
    
    # Ask if user wants to create a test invoice
    print()
    response = input("Create a test invoice for verification? (y/n): ")
    if response.lower() in ['y', 'yes']:
        create_test_invoice()
    
    print()
    print("Database initialization complete!")
    print()
