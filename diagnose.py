#!/usr/bin/env python3
"""
ATM Data Import Diagnostics Script
Specifically targets the 24 missing ATM records to identify import issues
"""

import psycopg2
import requests
import json
import logging
from datetime import datetime
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ATMDiagnostics:
    def __init__(self):
        self.conn = None
        self.connect_to_database()
        
    def connect_to_database(self):
        """Connect to PostgreSQL database"""
        try:
            self.conn = psycopg2.connect(
                host=os.getenv('DB_HOST', 'localhost'),
                database=os.getenv('DB_NAME', 'banking_locator'),
                user=os.getenv('DB_USER', 'postgres'),
                password=os.getenv('DB_PASSWORD', ''),
                port=os.getenv('DB_PORT', '5432')
            )
            logger.info("Successfully connected to database")
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise
    
    def fetch_fresh_atm_data(self):
        """Fetch fresh ATM data from Kapital Bank API"""
        logger.info("Fetching fresh ATM data from Kapital Bank API...")
        
        try:
            # This should match your scraper's ATM endpoint
            url = "https://kapitalbank.az/api/atm"  # Update with actual endpoint
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
                'Accept-Language': 'en-US,en;q=0.9',
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"Successfully fetched {len(data)} ATM records from API")
            return data
            
        except Exception as e:
            logger.error(f"Failed to fetch ATM data: {e}")
            return None
    
    def get_database_atm_data(self):
        """Get current ATM data from database"""
        logger.info("Fetching ATM data from database...")
        
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT name, address, lat, lon, created_at, updated_at
                FROM banking_locator.locations 
                WHERE company = 'Kapital Bank' AND type = 'atm'
                ORDER BY name, address
            """)
            
            db_data = cur.fetchall()
            logger.info(f"Found {len(db_data)} ATM records in database")
            return db_data
    
    def analyze_missing_records(self, api_data=None):
        """Analyze what specific records are missing"""
        logger.info("\n=== ANALYZING MISSING ATM RECORDS ===")
        
        # Get database data
        db_data = self.get_database_atm_data()
        db_addresses = set()
        db_names = set()
        
        for record in db_data:
            db_addresses.add(record[1])  # address
            db_names.add(record[0])      # name
        
        logger.info(f"Database has {len(db_data)} ATM records")
        logger.info(f"Unique addresses in DB: {len(db_addresses)}")
        logger.info(f"Unique names in DB: {len(db_names)}")
        
        # If we have fresh API data, compare
        if api_data:
            api_addresses = set()
            api_names = set()
            
            for record in api_data:
                # Adjust field names based on actual API response structure
                address = record.get('address', record.get('location', ''))
                name = record.get('name', record.get('title', ''))
                api_addresses.add(address)
                api_names.add(name)
            
            logger.info(f"API has {len(api_data)} ATM records")
            logger.info(f"Unique addresses in API: {len(api_addresses)}")
            logger.info(f"Unique names in API: {len(api_names)}")
            
            # Find missing addresses
            missing_addresses = api_addresses - db_addresses
            if missing_addresses:
                logger.warning(f"Found {len(missing_addresses)} addresses in API but not in DB:")
                for i, addr in enumerate(list(missing_addresses)[:10]):  # Show first 10
                    logger.warning(f"  {i+1}. {addr}")
                if len(missing_addresses) > 10:
                    logger.warning(f"  ... and {len(missing_addresses) - 10} more")
    
    def check_data_quality_issues(self):
        """Check for specific data quality issues in ATM records"""
        logger.info("\n=== ATM DATA QUALITY CHECK ===")
        
        with self.conn.cursor() as cur:
            # Check for ATMs with missing coordinates
            cur.execute("""
                SELECT COUNT(*) FROM banking_locator.locations 
                WHERE company = 'Kapital Bank' AND type = 'atm' 
                AND (lat IS NULL OR lon IS NULL)
            """)
            missing_coords = cur.fetchone()[0]
            logger.info(f"ATMs without coordinates: {missing_coords}")
            
            # Check for ATMs with invalid coordinates
            cur.execute("""
                SELECT COUNT(*) FROM banking_locator.locations 
                WHERE company = 'Kapital Bank' AND type = 'atm' 
                AND (lat < 38 OR lat > 42 OR lon < 44 OR lon > 52)
            """)
            invalid_coords = cur.fetchone()[0]
            logger.info(f"ATMs with coordinates outside Azerbaijan: {invalid_coords}")
            
            if invalid_coords > 0:
                cur.execute("""
                    SELECT name, address, lat, lon 
                    FROM banking_locator.locations 
                    WHERE company = 'Kapital Bank' AND type = 'atm' 
                    AND (lat < 38 OR lat > 42 OR lon < 44 OR lon > 52)
                    LIMIT 5
                """)
                logger.warning("Sample ATMs with invalid coordinates:")
                for row in cur.fetchall():
                    logger.warning(f"  {row[0]} - {row[1]} - Lat: {row[2]}, Lon: {row[3]}")
            
            # Check for duplicate ATMs
            cur.execute("""
                SELECT name, address, COUNT(*) as count
                FROM banking_locator.locations 
                WHERE company = 'Kapital Bank' AND type = 'atm'
                GROUP BY name, address
                HAVING COUNT(*) > 1
                ORDER BY count DESC
                LIMIT 10
            """)
            
            duplicates = cur.fetchall()
            if duplicates:
                logger.warning(f"Found {len(duplicates)} sets of duplicate ATMs:")
                for dup in duplicates:
                    logger.warning(f"  {dup[0]} - {dup[1]}: {dup[2]} duplicates")
            else:
                logger.info("✓ No duplicate ATMs found")
            
            # Check for ATMs with very long/short names or addresses
            cur.execute("""
                SELECT name, address, LENGTH(name) as name_len, LENGTH(address) as addr_len
                FROM banking_locator.locations 
                WHERE company = 'Kapital Bank' AND type = 'atm'
                AND (LENGTH(name) < 3 OR LENGTH(name) > 200 OR LENGTH(address) < 5 OR LENGTH(address) > 500)
                LIMIT 10
            """)
            
            length_issues = cur.fetchall()
            if length_issues:
                logger.warning("ATMs with unusual name/address lengths:")
                for issue in length_issues:
                    logger.warning(f"  Name({issue[2]}): {issue[0][:50]}...")
                    logger.warning(f"  Addr({issue[3]}): {issue[1][:50]}...")
            
            # Check for ATMs with special characters that might cause issues
            cur.execute("""
                SELECT name, address 
                FROM banking_locator.locations 
                WHERE company = 'Kapital Bank' AND type = 'atm'
                AND (name ~ '[^\x20-\x7E\u00C0-\u017F\u0400-\u04FF]' 
                     OR address ~ '[^\x20-\x7E\u00C0-\u017F\u0400-\u04FF]')
                LIMIT 5
            """)
            
            special_chars = cur.fetchall()
            if special_chars:
                logger.warning("ATMs with unusual characters:")
                for item in special_chars:
                    logger.warning(f"  {item[0]} - {item[1]}")
    
    def test_insert_simulation(self):
        """Simulate inserting a sample record to test for constraint issues"""
        logger.info("\n=== TESTING INSERT CONSTRAINTS ===")
        
        test_record = {
            'company': 'Kapital Bank',
            'type': 'atm',
            'name': 'Test ATM Location',
            'address': 'Test Address, Baku, Azerbaijan',
            'lat': 40.3755,
            'lon': 49.8328
        }
        
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO banking_locator.locations 
                    (company, type, name, address, lat, lon)
                    VALUES (%(company)s, %(type)s, %(name)s, %(address)s, %(lat)s, %(lon)s)
                    RETURNING id
                """, test_record)
                
                test_id = cur.fetchone()[0]
                logger.info(f"✓ Test insert successful, ID: {test_id}")
                
                # Clean up test record
                cur.execute("DELETE FROM banking_locator.locations WHERE id = %s", (test_id,))
                self.conn.commit()
                logger.info("✓ Test record cleaned up")
                
        except Exception as e:
            logger.error(f"✗ Test insert failed: {e}")
            self.conn.rollback()
    
    def generate_debug_sql(self):
        """Generate SQL queries to help debug the issue"""
        logger.info("\n=== DEBUG SQL QUERIES ===")
        
        queries = [
            "-- Find ATMs with longest names",
            """SELECT name, LENGTH(name) as len FROM banking_locator.locations 
               WHERE company = 'Kapital Bank' AND type = 'atm' 
               ORDER BY LENGTH(name) DESC LIMIT 5;""",
            
            "-- Find ATMs with longest addresses", 
            """SELECT address, LENGTH(address) as len FROM banking_locator.locations 
               WHERE company = 'Kapital Bank' AND type = 'atm' 
               ORDER BY LENGTH(address) DESC LIMIT 5;""",
            
            "-- Check for ATMs with NULL or empty fields",
            """SELECT COUNT(*), 
               COUNT(CASE WHEN name IS NULL OR name = '' THEN 1 END) as empty_names,
               COUNT(CASE WHEN address IS NULL OR address = '' THEN 1 END) as empty_addresses,
               COUNT(CASE WHEN lat IS NULL THEN 1 END) as null_lat,
               COUNT(CASE WHEN lon IS NULL THEN 1 END) as null_lon
               FROM banking_locator.locations 
               WHERE company = 'Kapital Bank' AND type = 'atm';""",
            
            "-- Find potential encoding issues",
            """SELECT name, address FROM banking_locator.locations 
               WHERE company = 'Kapital Bank' AND type = 'atm'
               AND (name != TRIM(name) OR address != TRIM(address))
               LIMIT 5;"""
        ]
        
        logger.info("Run these queries manually to debug:")
        for query in queries:
            logger.info(query)
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()

def main():
    """Main function"""
    diagnostics = None
    try:
        diagnostics = ATMDiagnostics()
        
        # Run all diagnostic checks
        diagnostics.check_data_quality_issues()
        diagnostics.test_insert_simulation()
        
        # Try to fetch fresh data for comparison
        fresh_data = diagnostics.fetch_fresh_atm_data()
        diagnostics.analyze_missing_records(fresh_data)
        
        diagnostics.generate_debug_sql()
        
        logger.info("\n=== RECOMMENDATIONS ===")
        logger.info("1. Check your scraper logs for specific error messages during ATM import")
        logger.info("2. Run the debug SQL queries above to identify problematic records")
        logger.info("3. Check if the 24 missing records have data quality issues")
        logger.info("4. Consider adding more detailed error logging to your scraper")
        
    except Exception as e:
        logger.error(f"Diagnostics failed: {e}")
    finally:
        if diagnostics:
            diagnostics.close()

if __name__ == "__main__":
    main()