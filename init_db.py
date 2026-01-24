#!/usr/bin/env python
"""
Database initialization script for FarmIQ
This script creates the database tables and initializes the database.
"""

import os
import sys

from sqlalchemy import inspect

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app"))

from app import app, db  # pylint: disable=wrong-import-position


def init_database():
    """Initialize the database by creating all tables"""
    with app.app_context():
        # Drop all tables (use with caution in production!)
        # db.drop_all()

        # Create all tables
        db.create_all()
        print("✅ Database tables created successfully!")
        print("📊 Tables created:")
        print("   - crop_predictions")
        print("   - fertilizer_predictions")
        print("   - disease_predictions")

        # Verify tables
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        print(f"\n✓ Total tables in database: {len(tables)}")
        for table in tables:
            print(f"  • {table}")


if __name__ == "__main__":
    print("🚀 Initializing FarmIQ Database...")
    init_database()
    print("\n✨ Database initialization complete!")
