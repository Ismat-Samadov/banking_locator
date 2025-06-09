#!/usr/bin/env python3
"""
Kapital Bank Location Scraper - FIXED VERSION
Scrapes location data from Kapital Bank API endpoints and saves to PostgreSQL database
Fixes duplicate detection and handles upsert logic properly
"""

import os
import json
import requests
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
import time
import logging
from typing import List, Dict, Optional
from dotenv import load_dotenv
import re

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class KapitalBankScraper:
    def __init__(self):
        # Check required environment variables
        required_env_vars = ['DB_HOST', 'DB_NAME', 'DB_USER', 'DB_PASSWORD']
        missing_vars = [var for var in required_env_vars if not os.environ.get(var)]
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
        
        # Database connection parameters
        self.db_params = {
            'host': os.environ.get('DB_HOST'),
            'database': os.environ.get('DB_NAME'),
            'user': os.environ.get('DB_USER'),
            'password': os.environ.get('DB_PASSWORD'),
            'port': int(os.environ.get('DB_PORT')),
            'sslmode': os.environ.get('DB_SSLMODE')
        }
        
        # Request headers
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8,ru;q=0.7,az;q=0.6',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'DNT': '1',
            'Sec-CH-UA': '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
            'Sec-CH-UA-Mobile': '?0',
            'Sec-CH-UA-Platform': '"macOS"',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': 'https://www.kapitalbank.az/locations/atm/all'
        }
        
        # API endpoints configuration
        self.endpoints = [
            {
                "name": "Branch locations",
                "company": "Kapital Bank",
                "description": "Retrieves a list of all branch offices, including their addresses and working hours.",
                "url": "https://www.kapitalbank.az/locations/region?is_nfc=false&weekend=false&type=branch",
                "type": "branch"
            },
            {
                "name": "ATM locations", 
                "company": "Kapital Bank",
                "description": "Retrieves a list of all ATMs, including their locations and availability.",
                "url": "https://www.kapitalbank.az/locations/region?is_nfc=false&weekend=false&type=atm",
                "type": "atm"
            },
            {
                "name": "Cash-in machines",
                "company": "Kapital Bank", 
                "description": "Retrieves a list of cash-in terminals, where customers can deposit cash.",
                "url": "https://www.kapitalbank.az/locations/region?is_nfc=false&weekend=false&type=cash_in",
                "type": "cash_in"
            },
            {
                "name": "Digital centers",
                "company": "Kapital Bank",
                "description": "Retrieves a list of digital service centers, offering self-service banking and digital support.",
                "url": "https://www.kapitalbank.az/locations/region?is_nfc=false&weekend=false&type=reqemsal-merkez",
                "type": "digital_center"
            },
            {
                "name": "Payment terminals",
                "company": "Kapital Bank",
                "description": "Retrieves a list of payment terminals for bill payments and other transactions.",
                "url": "https://www.kapitalbank.az/locations/region?is_nfc=false&weekend=false&type=payment_terminal",
                "type": "payment_terminal"
            }
        ]

    def normalize_text(self, text: str) -> str:
        """Normalize text for better duplicate detection"""
        if not text:
            return ""
        
        # Convert to lowercase and strip whitespace
        text = text.lower().strip()
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove common punctuation that might vary
        text = re.sub(r'[.,;:!?()"\'-]', '', text)
        
        return text

    def get_db_connection(self):
        """Establish database connection"""
        try:
            conn = psycopg2.connect(**self.db_params)
            return conn
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise

    def verify_table_exists(self):
        """Verify that the existing table exists and check its structure"""
        try:
            with self.get_db_connection() as conn:
                with conn.cursor() as cur:
                    # Check if table exists
                    cur.execute("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_schema = 'banking_locator' 
                            AND table_name = 'locations'
                        );
                    """)
                    
                    table_exists = cur.fetchone()[0]
                    
                    if not table_exists:
                        raise Exception("Table banking_locator.locations does not exist!")
                    
                    # Check table structure
                    cur.execute("""
                        SELECT column_name, data_type 
                        FROM information_schema.columns 
                        WHERE table_schema = 'banking_locator' 
                        AND table_name = 'locations'
                        ORDER BY ordinal_position;
                    """)
                    
                    columns = cur.fetchall()
                    column_names = [col[0] for col in columns]
                    
                    required_columns = ['id', 'company', 'type', 'name', 'address', 'lat', 'lon', 'created_at', 'updated_at']
                    missing_columns = [col for col in required_columns if col not in column_names]
                    
                    if missing_columns:
                        raise Exception(f"Missing required columns: {missing_columns}")
                    
                    logger.info("Existing table structure verified successfully")
                    logger.info(f"Available columns: {', '.join(column_names)}")
                    
        except Exception as e:
            logger.error(f"Error verifying table: {e}")
            raise

    def ensure_unique_constraint(self):
        """Ensure unique constraint exists to prevent duplicates"""
        try:
            with self.get_db_connection() as conn:
                with conn.cursor() as cur:
                    # Check if unique constraint exists
                    cur.execute("""
                        SELECT COUNT(*) FROM pg_constraint 
                        WHERE conrelid = 'banking_locator.locations'::regclass
                        AND conname = 'unique_company_type_name_address'
                    """)
                    
                    if cur.fetchone()[0] == 0:
                        logger.info("Adding unique constraint to prevent duplicates...")
                        cur.execute("""
                            ALTER TABLE banking_locator.locations 
                            ADD CONSTRAINT unique_company_type_name_address 
                            UNIQUE (company, type, name, address)
                        """)
                        conn.commit()
                        logger.info("✓ Unique constraint added successfully")
                    else:
                        logger.info("✓ Unique constraint already exists")
                        
        except Exception as e:
            logger.warning(f"Could not add unique constraint (may already exist): {e}")

    def fetch_endpoint_data(self, endpoint: Dict) -> Optional[List[Dict]]:
        """Fetch data from a single endpoint"""
        try:
            logger.info(f"Fetching data from: {endpoint['name']}")
            
            response = requests.get(
                endpoint['url'], 
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Successfully fetched {len(data)} records from {endpoint['name']}")
                return data
            else:
                logger.error(f"HTTP {response.status_code} for {endpoint['name']}")
                return None
                
        except requests.RequestException as e:
            logger.error(f"Request failed for {endpoint['name']}: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error for {endpoint['name']}: {e}")
            return None

    def process_location_data(self, raw_data: List[Dict], endpoint: Dict) -> List[Dict]:
        """Process raw API data into database format"""
        processed_locations = []
        seen_locations = set()  # Track duplicates within the same batch
        
        for item in raw_data:
            try:
                # Extract and validate coordinates
                lat = None
                lon = None
                
                if item.get('lat') and item.get('lng'):
                    try:
                        lat = float(item['lat'])
                        lon = float(item['lng'])
                        
                        # Validate coordinates are within reasonable bounds for Azerbaijan
                        if not (38 <= lat <= 42 and 44 <= lon <= 52):
                            logger.warning(f"Invalid coordinates for {item.get('name', 'unknown')}: {lat}, {lon}")
                            lat = lon = None
                    except (ValueError, TypeError):
                        logger.warning(f"Invalid coordinate format for {item.get('name', 'unknown')}")
                        lat = lon = None
                
                # Clean and validate required fields
                name = str(item.get('name', '')).strip()
                address = str(item.get('address', '')).strip()
                
                # Skip records with missing essential data
                if not name or not address:
                    logger.warning(f"Skipping record with missing name/address: {item}")
                    continue
                
                # Create normalized key for duplicate detection within batch
                normalized_key = (
                    endpoint['company'],
                    endpoint['type'],
                    self.normalize_text(name),
                    self.normalize_text(address)
                )
                
                # Skip if we've already seen this location in current batch
                if normalized_key in seen_locations:
                    logger.debug(f"Skipping duplicate in batch: {name}")
                    continue
                
                seen_locations.add(normalized_key)
                
                # Process location data
                location = {
                    'company': endpoint['company'],
                    'type': endpoint['type'],
                    'name': name,
                    'address': address,
                    'lat': lat,
                    'lon': lon,
                    'external_id': str(item.get('id', ''))  # Keep for logging
                }
                
                processed_locations.append(location)
                
            except Exception as e:
                logger.warning(f"Error processing location {item.get('id', 'unknown')}: {e}")
                continue
        
        logger.info(f"Processed {len(processed_locations)} unique locations from {len(raw_data)} raw records")
        return processed_locations

    def save_locations_to_db(self, locations: List[Dict], endpoint_name: str) -> tuple:
        """Save locations to database using UPSERT logic"""
        if not locations:
            return 0, 0
        
        # Use PostgreSQL UPSERT (ON CONFLICT) for better handling
        upsert_sql = """
        INSERT INTO banking_locator.locations 
        (company, type, name, address, lat, lon, created_at, updated_at)
        VALUES 
        (%(company)s, %(type)s, %(name)s, %(address)s, %(lat)s, %(lon)s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ON CONFLICT (company, type, name, address) 
        DO UPDATE SET 
            lat = EXCLUDED.lat,
            lon = EXCLUDED.lon,
            updated_at = CURRENT_TIMESTAMP
        RETURNING id, 
            CASE WHEN xmax = 0 THEN 'INSERT' ELSE 'UPDATE' END as operation
        """
        
        try:
            with self.get_db_connection() as conn:
                with conn.cursor() as cur:
                    inserted_count = 0
                    updated_count = 0
                    failed_count = 0
                    
                    for i, location in enumerate(locations):
                        try:
                            cur.execute(upsert_sql, location)
                            result = cur.fetchone()
                            
                            if result:
                                operation = result[1]
                                if operation == 'INSERT':
                                    inserted_count += 1
                                else:
                                    updated_count += 1
                            
                            # Progress logging for large batches
                            if (i + 1) % 100 == 0:
                                logger.debug(f"Processed {i + 1}/{len(locations)} records for {endpoint_name}")
                                
                        except psycopg2.IntegrityError as e:
                            # Handle specific constraint violations
                            logger.warning(f"Integrity error for location {location.get('name', 'unknown')}: {e}")
                            failed_count += 1
                            conn.rollback()
                            # Continue with next location
                            
                        except Exception as e:
                            logger.error(f"Error saving location {location.get('name', 'unknown')}: {e}")
                            failed_count += 1
                            conn.rollback()
                            # Continue with next location
                    
                    conn.commit()
                    
                    if failed_count > 0:
                        logger.warning(f"Failed to save {failed_count} locations")
                    
                    logger.info(f"Database operation completed: {inserted_count} inserted, {updated_count} updated, {failed_count} failed")
                    return inserted_count, updated_count
                    
        except Exception as e:
            logger.error(f"Error in batch save operation: {e}")
            raise

    def get_statistics(self):
        """Get database statistics"""
        try:
            with self.get_db_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # Get count by company and type
                    stats_sql = """
                    SELECT 
                        company,
                        type,
                        COUNT(*) as total_count,
                        MAX(updated_at) as last_updated
                    FROM banking_locator.locations 
                    WHERE company = 'Kapital Bank'
                    GROUP BY company, type
                    ORDER BY company, type
                    """
                    
                    cur.execute(stats_sql)
                    results = cur.fetchall()
                    
                    logger.info("=== DATABASE STATISTICS ===")
                    total_all = 0
                    for row in results:
                        logger.info(
                            f"{row['company']} - {row['type']}: "
                            f"{row['total_count']} total "
                            f"- Last updated: {row['last_updated']}"
                        )
                        total_all += row['total_count']
                    
                    logger.info(f"Total Kapital Bank locations: {total_all}")
                    return results
                    
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return []

    def run_scraper(self):
        """Main scraper execution"""
        logger.info("Starting Kapital Bank location scraper...")
        
        try:
            # Verify existing table structure
            self.verify_table_exists()
            
            # Ensure unique constraint exists
            self.ensure_unique_constraint()
            
            total_processed = 0
            total_inserted = 0
            total_updated = 0
            
            for endpoint in self.endpoints:
                try:
                    # Fetch data from endpoint
                    raw_data = self.fetch_endpoint_data(endpoint)
                    
                    if raw_data is None:
                        logger.warning(f"Skipping {endpoint['name']} due to fetch error")
                        continue
                    
                    # Process the data
                    processed_locations = self.process_location_data(raw_data, endpoint)
                    
                    if processed_locations:
                        # Save to database
                        inserted, updated = self.save_locations_to_db(processed_locations, endpoint['name'])
                        total_inserted += inserted
                        total_updated += updated
                        total_processed += len(processed_locations)
                    
                    # Add delay between requests to be respectful
                    time.sleep(2)
                    
                except Exception as e:
                    logger.error(f"Error processing endpoint {endpoint['name']}: {e}")
                    continue
            
            # Show final statistics
            self.get_statistics()
            
            logger.info(f"Scraping completed!")
            logger.info(f"Total locations processed: {total_processed}")
            logger.info(f"Total inserted: {total_inserted}")
            logger.info(f"Total updated: {total_updated}")
            
        except Exception as e:
            logger.error(f"Scraper execution failed: {e}")
            raise

def main():
    """Main execution function"""
    try:
        scraper = KapitalBankScraper()
        scraper.run_scraper()
    except Exception as e:
        logger.error(f"Scraper failed: {e}")
        raise

if __name__ == "__main__":
    main()