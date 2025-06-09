#!/usr/bin/env python3
"""
Fix ATM Duplicate Records Script
Automatically resolves the duplicate ATM issue causing 24 records to fail import
"""

import psycopg2
import os
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ATMDuplicateFixer:
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
    
    def analyze_duplicates(self):
        """Analyze the duplicate situation"""
        logger.info("=== ANALYZING DUPLICATE ATM RECORDS ===")
        
        with self.conn.cursor() as cur:
            # Get current stats
            cur.execute("""
                SELECT 
                    COUNT(*) as total_records,
                    COUNT(DISTINCT name || '|' || address) as unique_combinations
                FROM banking_locator.locations 
                WHERE company = 'Kapital Bank' AND type = 'atm'
            """)
            
            total, unique = cur.fetchone()
            duplicates = total - unique
            
            logger.info(f"Total ATM records: {total}")
            logger.info(f"Unique name+address combinations: {unique}")
            logger.info(f"Duplicate records: {duplicates}")
            
            if duplicates == 0:
                logger.info("✓ No duplicates found!")
                return False
            
            # Show duplicate examples
            cur.execute("""
                SELECT 
                    name,
                    address,
                    COUNT(*) as count,
                    string_agg(id::text, ', ') as record_ids
                FROM banking_locator.locations 
                WHERE company = 'Kapital Bank' AND type = 'atm'
                GROUP BY name, address
                HAVING COUNT(*) > 1
                ORDER BY COUNT(*) DESC
                LIMIT 10
            """)
            
            logger.info("Top duplicate records:")
            for row in cur.fetchall():
                logger.info(f"  '{row[0]}' at '{row[1]}': {row[2]} copies (IDs: {row[3]})")
            
            return True
    
    def check_coordinate_differences(self):
        """Check if duplicates have different coordinates (legitimate)"""
        logger.info("\n=== CHECKING COORDINATE DIFFERENCES ===")
        
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    name,
                    address,
                    COUNT(*) as total_records,
                    COUNT(DISTINCT lat || ',' || lon) as unique_coordinates,
                    string_agg(DISTINCT lat::text || ',' || lon::text, ' | ') as coordinates
                FROM banking_locator.locations 
                WHERE company = 'Kapital Bank' AND type = 'atm'
                GROUP BY name, address
                HAVING COUNT(*) > 1
                ORDER BY COUNT(DISTINCT lat || ',' || lon) DESC
                LIMIT 10
            """)
            
            coordinate_conflicts = []
            for row in cur.fetchall():
                name, address, total, unique_coords, coords = row
                if unique_coords > 1:
                    coordinate_conflicts.append(row)
                    logger.warning(f"COORDINATE CONFLICT: '{name}' has {unique_coords} different locations")
                    logger.warning(f"  Address: {address}")
                    logger.warning(f"  Coordinates: {coords}")
                else:
                    logger.info(f"True duplicate: '{name}' - same coordinates")
            
            return coordinate_conflicts
    
    def create_backup(self):
        """Create a backup of current data"""
        logger.info("\n=== CREATING BACKUP ===")
        
        backup_table = f"locations_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        with self.conn.cursor() as cur:
            cur.execute(f"""
                CREATE TABLE banking_locator.{backup_table} AS 
                SELECT * FROM banking_locator.locations
                WHERE company = 'Kapital Bank' AND type = 'atm'
            """)
            
            cur.execute(f"SELECT COUNT(*) FROM banking_locator.{backup_table}")
            backup_count = cur.fetchone()[0]
            
            logger.info(f"✓ Backup created: banking_locator.{backup_table}")
            logger.info(f"✓ Backup contains {backup_count} ATM records")
            
            self.conn.commit()
            return backup_table
    
    def remove_duplicates(self, handle_coordinate_conflicts=False):
        """Remove duplicate records, keeping the most recent"""
        logger.info("\n=== REMOVING DUPLICATE RECORDS ===")
        
        with self.conn.cursor() as cur:
            if handle_coordinate_conflicts:
                # More complex logic for coordinate conflicts
                logger.info("Using complex deduplication (preserving coordinate differences)...")
                
                # First, remove exact duplicates (same name, address, AND coordinates)
                cur.execute("""
                    DELETE FROM banking_locator.locations 
                    WHERE id IN (
                        SELECT id
                        FROM (
                            SELECT 
                                id,
                                ROW_NUMBER() OVER (
                                    PARTITION BY company, type, name, address, 
                                                ROUND(lat::numeric, 6), ROUND(lon::numeric, 6)
                                    ORDER BY created_at DESC, id DESC
                                ) as row_num
                            FROM banking_locator.locations 
                            WHERE company = 'Kapital Bank' AND type = 'atm'
                        ) ranked
                        WHERE row_num > 1
                    )
                """)
                
            else:
                # Simple deduplication by name+address
                logger.info("Using simple deduplication (by name+address)...")
                
                cur.execute("""
                    DELETE FROM banking_locator.locations 
                    WHERE id IN (
                        SELECT id
                        FROM (
                            SELECT 
                                id,
                                ROW_NUMBER() OVER (
                                    PARTITION BY company, type, name, address 
                                    ORDER BY created_at DESC, id DESC
                                ) as row_num
                            FROM banking_locator.locations 
                            WHERE company = 'Kapital Bank' AND type = 'atm'
                        ) ranked
                        WHERE row_num > 1
                    )
                """)
            
            deleted_count = cur.rowcount
            logger.info(f"✓ Removed {deleted_count} duplicate records")
            
            # Get new stats
            cur.execute("""
                SELECT 
                    COUNT(*) as total_records,
                    COUNT(DISTINCT name || '|' || address) as unique_combinations
                FROM banking_locator.locations 
                WHERE company = 'Kapital Bank' AND type = 'atm'
            """)
            
            total, unique = cur.fetchone()
            logger.info(f"✓ After cleanup: {total} total records, {unique} unique combinations")
            
            self.conn.commit()
            return deleted_count
    
    def add_unique_constraint(self):
        """Add unique constraint to prevent future duplicates"""
        logger.info("\n=== ADDING UNIQUE CONSTRAINT ===")
        
        with self.conn.cursor() as cur:
            try:
                # Check if constraint already exists
                cur.execute("""
                    SELECT COUNT(*) FROM pg_constraint 
                    WHERE conrelid = 'banking_locator.locations'::regclass
                    AND conname = 'unique_company_type_name_address'
                """)
                
                if cur.fetchone()[0] > 0:
                    logger.info("✓ Unique constraint already exists")
                    return
                
                # Add the constraint
                cur.execute("""
                    ALTER TABLE banking_locator.locations 
                    ADD CONSTRAINT unique_company_type_name_address 
                    UNIQUE (company, type, name, address)
                """)
                
                logger.info("✓ Added unique constraint: unique_company_type_name_address")
                self.conn.commit()
                
            except Exception as e:
                logger.error(f"Failed to add unique constraint: {e}")
                self.conn.rollback()
    
    def verify_fix(self):
        """Verify that the fix worked"""
        logger.info("\n=== VERIFYING FIX ===")
        
        with self.conn.cursor() as cur:
            # Check final stats
            cur.execute("""
                SELECT 
                    COUNT(*) as total_records,
                    COUNT(DISTINCT name || '|' || address) as unique_combinations
                FROM banking_locator.locations 
                WHERE company = 'Kapital Bank' AND type = 'atm'
            """)
            
            total, unique = cur.fetchone()
            
            if total == unique:
                logger.info(f"✅ SUCCESS: {total} ATM records, all unique!")
                logger.info(f"✅ Ready to import the remaining {1130 - total} ATM records")
            else:
                logger.warning(f"⚠️  Still have duplicates: {total} total, {unique} unique")
            
            # Check if we're closer to the expected 1130
            missing = 1130 - total
            logger.info(f"📊 Missing records to reach 1130: {missing}")
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()

def main():
    """Main function"""
    fixer = None
    try:
        fixer = ATMDuplicateFixer()
        
        # Step 1: Analyze the situation
        has_duplicates = fixer.analyze_duplicates()
        
        if not has_duplicates:
            logger.info("No duplicates found. The issue might be elsewhere.")
            return
        
        # Step 2: Check for coordinate conflicts
        coordinate_conflicts = fixer.check_coordinate_differences()
        
        # Step 3: Ask user for confirmation
        print(f"\nFound duplicates. Coordinate conflicts: {len(coordinate_conflicts)}")
        print("This will:")
        print("1. Create a backup of current ATM data")
        print("2. Remove duplicate records (keeping the most recent)")
        print("3. Add a unique constraint to prevent future duplicates")
        print("4. Allow your scraper to import the missing 24 records")
        
        response = input("\nProceed with the fix? (y/n): ")
        if response.lower() != 'y':
            logger.info("Fix cancelled by user")
            return
        
        # Step 4: Create backup
        backup_table = fixer.create_backup()
        
        # Step 5: Remove duplicates
        handle_conflicts = len(coordinate_conflicts) > 0
        deleted = fixer.remove_duplicates(handle_conflicts)
        
        # Step 6: Add unique constraint
        fixer.add_unique_constraint()
        
        # Step 7: Verify fix
        fixer.verify_fix()
        
        logger.info(f"\n🎉 FIX COMPLETED!")
        logger.info(f"📁 Backup saved as: {backup_table}")
        logger.info(f"🗑️  Removed {deleted} duplicate records")
        logger.info(f"🔄 Now re-run your scraper - it should import all 1130 ATM records!")
        
    except Exception as e:
        logger.error(f"Fix failed: {e}")
    finally:
        if fixer:
            fixer.close()

if __name__ == "__main__":
    main()