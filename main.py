import os
import json
import logging
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session
import google.generativeai as genai
import psycopg2
from psycopg2.extras import RealDictCursor

from dotenv import load_dotenv
load_dotenv()
import math
from typing import Dict, List, Optional, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY')

# Configure Gemini API
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    logger.error("GEMINI_API_KEY environment variable not set")
    raise ValueError("Please set GEMINI_API_KEY environment variable")

genai.configure(api_key=GEMINI_API_KEY)

# Database configuration
DB_CONFIG = {
    'host': os.environ.get('DB_HOST'),
    'database': os.environ.get('DB_NAME'),
    'user': os.environ.get('DB_USER'),
    'password': os.environ.get('DB_PASSWORD'),
    'port': os.environ.get('DB_PORT'),
    'sslmode': os.environ.get('DB_SSLMODE')
}

# Validate required environment variables
required_env_vars = ['SECRET_KEY', 'GEMINI_API_KEY', 'DB_HOST', 'DB_NAME', 'DB_USER', 'DB_PASSWORD', 'DB_PORT', 'DB_SSLMODE']
missing_vars = [var for var in required_env_vars if not os.environ.get(var)]
if missing_vars:
    logger.error(f"Missing required environment variables: {missing_vars}")
    raise ValueError(f"Please set the following environment variables: {missing_vars}")

class DatabaseManager:
    """Database connection and query management"""
    
    def __init__(self, config):
        self.config = config
        
    def get_connection(self):
        """Get database connection"""
        try:
            conn = psycopg2.connect(**self.config)
            return conn
        except Exception as e:
            logger.error(f"Database connection error: {str(e)}")
            raise
    
    def execute_query(self, query, params=None, fetch_all=True):
        """Execute database query"""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute(query, params)
                    if fetch_all:
                        return cursor.fetchall()
                    else:
                        return cursor.fetchone()
        except Exception as e:
            logger.error(f"Database query error: {str(e)}")
            raise

class LocationService:
    """Location-based services for banking locations"""
    
    @staticmethod
    def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points using Haversine formula"""
        # Convert latitude and longitude from degrees to radians
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        # Radius of earth in kilometers
        r = 6371
        return c * r
    
    @staticmethod
    def get_user_location(request) -> Tuple[Optional[float], Optional[float]]:
        """Extract user location from request"""
        try:
            # Try to get location from query parameters
            lat = request.args.get('lat')
            lon = request.args.get('lon')
            
            if lat and lon:
                return float(lat), float(lon)
                
            # Try to get location from JSON body
            data = request.get_json()
            if data and 'location' in data:
                location = data['location']
                if 'lat' in location and 'lon' in location:
                    return float(location['lat']), float(location['lon'])
                    
            return None, None
        except (ValueError, TypeError):
            return None, None

class BankingAssistant:
    """Banking Assistant with Database Integration"""
    
    def __init__(self):
        # Initialize Gemini model
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        self.db_manager = DatabaseManager(DB_CONFIG)
        self.location_service = LocationService()
        
        # System prompt for the assistant
        self.system_prompt = """You are a helpful and knowledgeable banking assistant with access to real-time banking location data.

You help users with:
- Finding nearest banks, ATMs, and financial services
- General banking services information
- Account types and features
- Banking products (loans, deposits, cards)
- Digital banking guidance
- General banking advice and best practices
- Financial literacy and education
- Security tips and fraud prevention

You have access to a comprehensive database of banking locations including:
- Bank branches and their exact addresses
- ATM locations
- Different types of banking services available at each location
- Real-time distance calculations from user's location

You should:
- Be friendly, professional, and helpful
- Provide accurate banking information based on real data
- Help users find the nearest banking services to their location
- Explain banking concepts clearly
- Help users understand their banking options
- Prioritize user security and privacy
- Provide educational content about banking
- Give general guidance on financial matters

Important guidelines:
- Never ask for or handle actual account numbers or sensitive personal information
- Always recommend contacting the user's bank directly for account-specific issues
- Provide general information rather than specific financial advice
- Emphasize security best practices
- Be educational and informative
- When providing location-based services, always respect user privacy

Remember: You're here to educate and guide users about banking services and help them find convenient banking locations, not to handle actual banking transactions or provide specific financial advice."""

    def get_nearby_locations(self, user_lat: float, user_lon: float, limit: int = 10, max_distance: float = 50.0) -> List[Dict]:
        """Get nearby banking locations"""
        try:
            query = """
            SELECT id, company, type, name, address, lat, lon, created_at, updated_at
            FROM banking_locator.locations
            WHERE lat IS NOT NULL AND lon IS NOT NULL
            """
            
            locations = self.db_manager.execute_query(query)
            
            # Calculate distances and filter
            nearby_locations = []
            for location in locations:
                distance = self.location_service.calculate_distance(
                    user_lat, user_lon, float(location['lat']), float(location['lon'])
                )
                
                if distance <= max_distance:
                    location_dict = dict(location)
                    location_dict['distance'] = round(distance, 2)
                    nearby_locations.append(location_dict)
            
            # Sort by distance and limit results
            nearby_locations.sort(key=lambda x: x['distance'])
            return nearby_locations[:limit]
            
        except Exception as e:
            logger.error(f"Error getting nearby locations: {str(e)}")
            return []

    def get_all_locations(self, company_filter: str = None, type_filter: str = None) -> List[Dict]:
        """Get all banking locations with optional filters"""
        try:
            query = """
            SELECT id, company, type, name, address, lat, lon, created_at, updated_at
            FROM banking_locator.locations
            WHERE 1=1
            """
            params = []
            
            if company_filter:
                query += " AND LOWER(company) LIKE LOWER(%s)"
                params.append(f"%{company_filter}%")
                
            if type_filter:
                query += " AND LOWER(type) LIKE LOWER(%s)"
                params.append(f"%{type_filter}%")
                
            query += " ORDER BY company, name"
            
            locations = self.db_manager.execute_query(query, params)
            return [dict(location) for location in locations]
            
        except Exception as e:
            logger.error(f"Error getting all locations: {str(e)}")
            return []

    def get_companies(self) -> List[str]:
        """Get list of all banking companies"""
        try:
            query = "SELECT DISTINCT company FROM banking_locator.locations WHERE company IS NOT NULL ORDER BY company"
            companies = self.db_manager.execute_query(query)
            return [company['company'] for company in companies]
        except Exception as e:
            logger.error(f"Error getting companies: {str(e)}")
            return []

    def get_location_types(self) -> List[str]:
        """Get list of all location types"""
        try:
            query = "SELECT DISTINCT type FROM banking_locator.locations WHERE type IS NOT NULL ORDER BY type"
            types = self.db_manager.execute_query(query)
            return [location_type['type'] for location_type in types]
        except Exception as e:
            logger.error(f"Error getting location types: {str(e)}")
            return []

    def format_locations_for_ai(self, locations: List[Dict], user_lat: float = None, user_lon: float = None) -> str:
        """Format locations data for AI context"""
        if not locations:
            return "No banking locations found."
        
        formatted = "Banking Locations:\n"
        for i, location in enumerate(locations, 1):
            distance_info = f" (Distance: {location.get('distance', 'N/A')} km)" if 'distance' in location else ""
            formatted += f"{i}. {location['company']} - {location['name']}\n"
            formatted += f"   Type: {location['type']}\n"
            formatted += f"   Address: {location['address']}{distance_info}\n\n"
        
        return formatted

    def get_chat_response(self, user_message: str, conversation_history: List[Dict] = None, user_location: Tuple[float, float] = None) -> str:
        """Get response from Gemini AI with location context"""
        try:
            # Check if message is location-related
            location_keywords = ['near', 'nearby', 'closest', 'find', 'locate', 'atm', 'branch', 'bank', 'location', 'address', 'where']
            is_location_query = any(keyword in user_message.lower() for keyword in location_keywords)
            
            # Prepare conversation context
            context = f"{self.system_prompt}\n\n"
            
            # Add location data if available and relevant
            if user_location and is_location_query:
                user_lat, user_lon = user_location
                nearby_locations = self.get_nearby_locations(user_lat, user_lon)
                if nearby_locations:
                    context += f"User's location: {user_lat}, {user_lon}\n"
                    context += f"{self.format_locations_for_ai(nearby_locations, user_lat, user_lon)}\n"
                else:
                    context += "No nearby banking locations found within 50km radius.\n\n"
            
            # Add general banking data context
            companies = self.get_companies()
            types = self.get_location_types()
            context += f"Available banking companies: {', '.join(companies)}\n"
            context += f"Available service types: {', '.join(types)}\n\n"
            
            # Add conversation history if available
            if conversation_history:
                context += "Previous conversation:\n"
                for msg in conversation_history[-5:]:  # Last 5 messages for context
                    context += f"{msg['role']}: {msg['content']}\n"
            
            # Add current user message
            context += f"User: {user_message}\nAssistant:"
            
            # Generate response
            response = self.model.generate_content(context)
            
            if response.text:
                return response.text.strip()
            else:
                return "I apologize, but I'm having trouble processing your request right now. Please try again."
                
        except Exception as e:
            logger.error(f"Error generating chat response: {str(e)}")
            return "I'm experiencing technical difficulties. Please try again in a moment."

# Initialize the assistant
banking_assistant = BankingAssistant()

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    """Handle chat messages"""
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return jsonify({'error': 'Message is required'}), 400
        
        # Get user location if provided
        user_location = None
        if 'location' in data:
            lat = data['location'].get('lat')
            lon = data['location'].get('lon')
            if lat is not None and lon is not None:
                user_location = (float(lat), float(lon))
        
        # Get or create conversation history from session
        if 'conversation' not in session:
            session['conversation'] = []
        
        # Add user message to history
        session['conversation'].append({
            'role': 'user',
            'content': user_message,
            'timestamp': datetime.now().isoformat()
        })
        
        # Get AI response with location context
        ai_response = banking_assistant.get_chat_response(
            user_message, 
            session['conversation'],
            user_location
        )
        
        # Add AI response to history
        session['conversation'].append({
            'role': 'assistant', 
            'content': ai_response,
            'timestamp': datetime.now().isoformat()
        })
        
        # Keep only last 20 messages to prevent session from growing too large
        if len(session['conversation']) > 20:
            session['conversation'] = session['conversation'][-20:]
        
        return jsonify({
            'response': ai_response,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/locations/nearby', methods=['GET', 'POST'])
def nearby_locations():
    """Get nearby banking locations"""
    try:
        # Get user location
        if request.method == 'POST':
            data = request.get_json()
            lat = data.get('lat')
            lon = data.get('lon')
        else:
            lat = request.args.get('lat')
            lon = request.args.get('lon')
        
        if not lat or not lon:
            return jsonify({'error': 'Latitude and longitude are required'}), 400
        
        lat, lon = float(lat), float(lon)
        limit = int(request.args.get('limit', 10))
        max_distance = float(request.args.get('max_distance', 50.0))
        
        locations = banking_assistant.get_nearby_locations(lat, lon, limit, max_distance)
        
        return jsonify({
            'locations': locations,
            'user_location': {'lat': lat, 'lon': lon},
            'total_found': len(locations)
        })
        
    except Exception as e:
        logger.error(f"Error in nearby locations endpoint: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/locations', methods=['GET'])
def get_locations():
    """Get all banking locations with optional filters"""
    try:
        company_filter = request.args.get('company')
        type_filter = request.args.get('type')
        
        locations = banking_assistant.get_all_locations(company_filter, type_filter)
        
        return jsonify({
            'locations': locations,
            'total_found': len(locations),
            'filters': {
                'company': company_filter,
                'type': type_filter
            }
        })
        
    except Exception as e:
        logger.error(f"Error in locations endpoint: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/companies', methods=['GET'])
def get_companies():
    """Get list of banking companies"""
    try:
        companies = banking_assistant.get_companies()
        return jsonify({'companies': companies})
    except Exception as e:
        logger.error(f"Error in companies endpoint: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/location-types', methods=['GET'])
def get_location_types():
    """Get list of location types"""
    try:
        types = banking_assistant.get_location_types()
        return jsonify({'types': types})
    except Exception as e:
        logger.error(f"Error in location types endpoint: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/clear-chat', methods=['POST'])
def clear_chat():
    """Clear chat history"""
    try:
        session['conversation'] = []
        return jsonify({'message': 'Chat history cleared'})
    except Exception as e:
        logger.error(f"Error clearing chat: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/health')
def health_check():
    """Health check endpoint for deployment"""
    try:
        # Test database connection
        banking_assistant.db_manager.execute_query("SELECT 1", fetch_all=False)
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'service': 'Banking Assistant',
            'database': 'connected'
        })
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'timestamp': datetime.now().isoformat(),
            'service': 'Banking Assistant',
            'database': 'disconnected',
            'error': str(e)
        }), 503

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return render_template('index.html'), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {str(error)}")
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    
    # Run the app
    app.run(
        host='0.0.0.0',
        port=port,
        debug=os.environ.get('FLASK_ENV') == 'development'
    )