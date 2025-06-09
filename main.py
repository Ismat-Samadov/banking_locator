from flask import Flask, render_template, request, jsonify
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv
import math
from datetime import datetime

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST'),
    'database': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'port': os.getenv('DB_PORT'),
    'sslmode': os.getenv('DB_SSLMODE')
}

def get_db_connection():
    """Create and return a database connection"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees)
    Returns distance in kilometers
    """
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    # Radius of earth in kilometers
    r = 6371
    return c * r

@app.route('/api/test')
def test_api():
    """Test endpoint to verify API is working"""
    return jsonify({
        'success': True,
        'message': 'API is working',
        'timestamp': str(datetime.now()) if 'datetime' in globals() else 'unknown'
    })

@app.route('/api/db-test')
def test_db():
    """Test database connection"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM banking_locator.locations")
        count = cursor.fetchone()[0]
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'Database connected successfully. Found {count} locations.',
            'count': count
        })
        
    except Exception as e:
        return jsonify({'error': f'Database error: {str(e)}'}), 500

@app.route('/test.html')
def test_page():
    """Test page for debugging"""
    return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Banking App Test</title>
    <style>
        body { font-family: Arial, sans-serif; padding: 20px; }
        .test-section { margin: 20px 0; padding: 15px; border: 1px solid #ccc; }
        .success { background: #d4edda; color: #155724; padding: 10px; margin: 5px 0; }
        .error { background: #f8d7da; color: #721c24; padding: 10px; margin: 5px 0; }
        button { padding: 10px 15px; margin: 5px; cursor: pointer; background: #007bff; color: white; border: none; }
        button:hover { background: #0056b3; }
    </style>
</head>
<body>
    <h1>Banking Locator App Test</h1>
    
    <div class="test-section">
        <h3>Test 1: Basic JavaScript</h3>
        <button onclick="testJS()">Test JavaScript</button>
        <div id="js-result"></div>
    </div>
    
    <div class="test-section">
        <h3>Test 2: API Connectivity</h3>
        <button onclick="testAPI()">Test API</button>
        <div id="api-result"></div>
    </div>
    
    <div class="test-section">
        <h3>Test 3: Database Connection</h3>
        <button onclick="testDB()">Test Database</button>
        <div id="db-result"></div>
    </div>
    
    <div class="test-section">
        <h3>Test 4: Geolocation</h3>
        <button onclick="testLocation()">Test Location</button>
        <div id="location-result"></div>
    </div>
    
    <div class="test-section">
        <h3>Test 5: Search API</h3>
        <button onclick="testSearch()">Test Search (Baku Location)</button>
        <div id="search-result"></div>
    </div>

    <div class="test-section">
        <h3>Go to Main App</h3>
        <a href="/" style="display: inline-block; padding: 10px 15px; background: #28a745; color: white; text-decoration: none;">Go to Main Banking App</a>
    </div>

    <script>
        console.log("Test page loaded");
        
        function testJS() {
            console.log("JavaScript test clicked");
            document.getElementById('js-result').innerHTML = '<div class="success">✓ JavaScript is working!</div>';
        }
        
        async function testAPI() {
            console.log("Testing API...");
            try {
                const response = await fetch('/api/test');
                console.log("API response:", response);
                const data = await response.json();
                console.log("API data:", data);
                document.getElementById('api-result').innerHTML = `<div class="success">✓ API Working: ${data.message}</div>`;
            } catch (error) {
                console.error("API error:", error);
                document.getElementById('api-result').innerHTML = `<div class="error">✗ API Error: ${error.message}</div>`;
            }
        }
        
        async function testDB() {
            console.log("Testing database...");
            try {
                const response = await fetch('/api/db-test');
                console.log("DB response:", response);
                const data = await response.json();
                console.log("DB data:", data);
                if (data.success) {
                    document.getElementById('db-result').innerHTML = `<div class="success">✓ ${data.message}</div>`;
                } else {
                    document.getElementById('db-result').innerHTML = `<div class="error">✗ Database Error: ${data.error}</div>`;
                }
            } catch (error) {
                console.error("DB error:", error);
                document.getElementById('db-result').innerHTML = `<div class="error">✗ Database Connection Error: ${error.message}</div>`;
            }
        }
        
        function testLocation() {
            console.log("Testing location...");
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(
                    (position) => {
                        console.log("Location success:", position);
                        document.getElementById('location-result').innerHTML = 
                            `<div class="success">✓ Location: ${position.coords.latitude}, ${position.coords.longitude}</div>`;
                    },
                    (error) => {
                        console.error("Location error:", error);
                        document.getElementById('location-result').innerHTML = 
                            `<div class="error">✗ Location Error: ${error.message}</div>`;
                    }
                );
            } else {
                document.getElementById('location-result').innerHTML = 
                    '<div class="error">✗ Geolocation not supported</div>';
            }
        }
        
        async function testSearch() {
            console.log("Testing search...");
            try {
                const requestData = {
                    latitude: 40.4093,
                    longitude: 49.8671,
                    radius: 10,
                    type: 'all',
                    limit: 5
                };
                console.log("Search request:", requestData);
                
                const response = await fetch('/api/nearby-locations', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(requestData)
                });
                
                console.log("Search response:", response);
                const data = await response.json();
                console.log("Search data:", data);
                
                if (data.success) {
                    document.getElementById('search-result').innerHTML = 
                        `<div class="success">✓ Found ${data.count} locations</div>`;
                } else {
                    document.getElementById('search-result').innerHTML = 
                        `<div class="error">✗ Search Error: ${data.error}</div>`;
                }
            } catch (error) {
                console.error("Search error:", error);
                document.getElementById('search-result').innerHTML = 
                    `<div class="error">✗ Search Request Error: ${error.message}</div>`;
            }
        }
    </script>
</body>
</html>'''

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')

@app.route('/api/nearby-locations', methods=['POST'])
def get_nearby_locations():
    """
    API endpoint to get nearby banking locations
    Expects JSON with user's latitude and longitude
    """
    try:
        print("Nearby locations API called")
        data = request.get_json()
        print(f"Received data: {data}")
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        user_lat = float(data.get('latitude'))
        user_lon = float(data.get('longitude'))
        radius = float(data.get('radius', 10))  # Default 10km radius
        limit = int(data.get('limit', 20))  # Default 20 locations
        service_type = data.get('type', 'all')  # Filter by service type
        
        print(f"User location: {user_lat}, {user_lon}")
        print(f"Search radius: {radius}km, Service type: {service_type}")
        
        conn = get_db_connection()
        if not conn:
            print("Database connection failed")
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Build query based on service type filter
        base_query = """
            SELECT id, company, type, name, address, lat, lon, created_at, updated_at
            FROM banking_locator.locations
            WHERE lat IS NOT NULL AND lon IS NOT NULL
        """
        
        params = []
        if service_type != 'all':
            base_query += " AND type = %s"
            params.append(service_type)
        
        print(f"Executing query: {base_query}")
        print(f"Query params: {params}")
        
        cursor.execute(base_query, params)
        locations = cursor.fetchall()
        
        print(f"Found {len(locations)} locations in database")
        
        # Calculate distances and filter by radius
        nearby_locations = []
        for location in locations:
            try:
                distance = calculate_distance(
                    user_lat, user_lon, 
                    float(location['lat']), float(location['lon'])
                )
                
                if distance <= radius:
                    location_dict = dict(location)
                    location_dict['distance'] = round(distance, 2)
                    nearby_locations.append(location_dict)
            except (ValueError, TypeError) as e:
                print(f"Error processing location {location.get('id')}: {e}")
                continue
        
        print(f"Found {len(nearby_locations)} locations within {radius}km")
        
        # Sort by distance and limit results
        nearby_locations.sort(key=lambda x: x['distance'])
        nearby_locations = nearby_locations[:limit]
        
        conn.close()
        
        result = {
            'success': True,
            'locations': nearby_locations,
            'count': len(nearby_locations)
        }
        
        print(f"Returning {len(nearby_locations)} locations")
        return jsonify(result)
        
    except Exception as e:
        print(f"Error in get_nearby_locations: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/location-types')
def get_location_types():
    """Get all available service types"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT type FROM banking_locator.locations WHERE type IS NOT NULL ORDER BY type")
        types = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        
        return jsonify({
            'success': True,
            'types': types
        })
        
    except Exception as e:
        print(f"Error in get_location_types: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/companies')
def get_companies():
    """Get all available companies"""
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT company FROM banking_locator.locations WHERE company IS NOT NULL ORDER BY company")
        companies = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        
        return jsonify({
            'success': True,
            'companies': companies
        })
        
    except Exception as e:
        print(f"Error in get_companies: {e}")
        return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(debug=os.getenv('FLASK_ENV') == 'development', host='0.0.0.0', port=port)