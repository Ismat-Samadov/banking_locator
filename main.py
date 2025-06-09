import os
import json
import logging
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session
import requests
from typing import Dict, List, Optional, Tuple
import math

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')

class LocationBankingService:
    """Location-based Banking Service"""
    
    def __init__(self):
        # Sample banking locations data (replace with real database)
        self.banking_locations = {
            "Azerbaijan": {
                "Baku": [
                    {
                        "id": 1,
                        "name": "Kapital Bank - 28 May Branch",
                        "type": "bank",
                        "address": "28 May Street 15, Baku",
                        "lat": 40.3777,
                        "lng": 49.8920,
                        "phone": "+994 12 596 33 33",
                        "hours": "Mon-Fri: 9:00-18:00, Sat: 9:00-15:00",
                        "services": ["ATM", "Currency Exchange", "Loans", "Deposits"],
                        "has_atm": True
                    },
                    {
                        "id": 2,
                        "name": "International Bank of Azerbaijan - Nizami Branch",
                        "type": "bank",
                        "address": "Nizami Street 96, Baku",
                        "lat": 40.3656,
                        "lng": 49.8348,
                        "phone": "+994 12 493 10 19",
                        "hours": "Mon-Fri: 9:00-17:30",
                        "services": ["ATM", "International Transfers", "Business Banking"],
                        "has_atm": True
                    },
                    {
                        "id": 3,
                        "name": "Pasha Bank ATM - Fountain Square",
                        "type": "atm",
                        "address": "Fountain Square, Baku",
                        "lat": 40.3656,
                        "lng": 49.8348,
                        "phone": "+994 12 496 86 86",
                        "hours": "24/7",
                        "services": ["ATM", "Cash Withdrawal", "Balance Inquiry"],
                        "has_atm": True
                    },
                    {
                        "id": 4,
                        "name": "Yelo Bank - Ganjlik Branch",
                        "type": "bank",
                        "address": "Ganjlik Mall, Baku",
                        "lat": 40.4093,
                        "lng": 49.8671,
                        "phone": "+994 12 404 04 04",
                        "hours": "Mon-Sun: 10:00-22:00",
                        "services": ["ATM", "Quick Loans", "Mobile Banking"],
                        "has_atm": True
                    }
                ],
                "Ganja": [
                    {
                        "id": 5,
                        "name": "Bank of Baku - Ganja Central",
                        "type": "bank",
                        "address": "Nizami Street 1, Ganja",
                        "lat": 40.6828,
                        "lng": 46.3611,
                        "phone": "+994 22 256 55 55",
                        "hours": "Mon-Fri: 9:00-17:00",
                        "services": ["ATM", "Deposits", "Personal Banking"],
                        "has_atm": True
                    }
                ]
            },
            "Turkey": {
                "Istanbul": [
                    {
                        "id": 6,
                        "name": "Garanti BBVA - Taksim Branch",
                        "type": "bank",
                        "address": "Taksim Square, Istanbul",
                        "lat": 41.0370,
                        "lng": 28.9857,
                        "phone": "+90 444 0 333",
                        "hours": "Mon-Fri: 9:00-17:00",
                        "services": ["ATM", "International Banking", "Currency Exchange"],
                        "has_atm": True
                    }
                ]
            }
        }
        
        # Currency exchange rates (mock data - use real API in production)
        self.exchange_rates = {
            "AZN": {"USD": 0.588, "EUR": 0.541, "TRY": 20.15, "RUB": 54.2},
            "USD": {"AZN": 1.70, "EUR": 0.92, "TRY": 34.25, "RUB": 92.15},
            "EUR": {"AZN": 1.85, "USD": 1.09, "TRY": 37.32, "RUB": 100.45}
        }

    def reverse_geocode(self, lat: float, lng: float) -> Dict:
        """Get location information from coordinates using OpenStreetMap Nominatim"""
        try:
            url = f"https://nominatim.openstreetmap.org/reverse"
            params = {
                "format": "json",
                "lat": lat,
                "lon": lng,
                "addressdetails": 1,
                "accept-language": "en"
            }
            headers = {
                "User-Agent": "BankingLocator/1.0"
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=5)
            if response.ok:
                return response.json()
            return {}
        except Exception as e:
            logger.error(f"Geocoding error: {str(e)}")
            return {}

    def calculate_distance(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """Calculate distance between two points using Haversine formula"""
        R = 6371  # Earth's radius in kilometers
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lng = math.radians(lng2 - lng1)
        
        a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lng/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        distance = R * c
        
        return round(distance, 2)

    def find_nearby_banking(self, lat: float, lng: float, radius: float = 10.0) -> List[Dict]:
        """Find nearby banking locations within radius (km)"""
        nearby_locations = []
        
        for country, cities in self.banking_locations.items():
            for city, locations in cities.items():
                for location in locations:
                    distance = self.calculate_distance(lat, lng, location["lat"], location["lng"])
                    if distance <= radius:
                        location_with_distance = location.copy()
                        location_with_distance["distance"] = distance
                        location_with_distance["country"] = country
                        location_with_distance["city"] = city
                        nearby_locations.append(location_with_distance)
        
        # Sort by distance
        nearby_locations.sort(key=lambda x: x["distance"])
        return nearby_locations

    def get_location_info(self, lat: float, lng: float) -> Dict:
        """Get comprehensive location-based banking information"""
        # Reverse geocode to get address details
        geocode_result = self.reverse_geocode(lat, lng)
        
        # Extract location information
        address_info = {}
        if geocode_result:
            address = geocode_result.get("address", {})
            address_info = {
                "display_name": geocode_result.get("display_name", "Unknown Location"),
                "country": address.get("country", "Unknown"),
                "city": address.get("city") or address.get("town") or address.get("village", "Unknown"),
                "postcode": address.get("postcode", ""),
                "road": address.get("road", ""),
                "country_code": address.get("country_code", "").upper()
            }
        
        # Find nearby banking locations
        nearby_banking = self.find_nearby_banking(lat, lng)
        
        # Get relevant exchange rates
        country_code = address_info.get("country_code", "AZ")
        base_currency = "AZN" if country_code == "AZ" else "USD"
        relevant_rates = self.exchange_rates.get(base_currency, {})
        
        return {
            "coordinates": {"lat": lat, "lng": lng},
            "address": address_info,
            "nearby_banking": nearby_banking,
            "exchange_rates": relevant_rates,
            "base_currency": base_currency,
            "timestamp": datetime.now().isoformat()
        }

# Initialize the service
banking_service = LocationBankingService()

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')

@app.route('/api/location-info', methods=['POST'])
def location_info():
    """Get location-based banking information"""
    try:
        data = request.get_json()
        lat = data.get('lat')
        lng = data.get('lng')
        
        if not lat or not lng:
            return jsonify({'error': 'Latitude and longitude are required'}), 400
        
        # Validate coordinates
        if not (-90 <= float(lat) <= 90) or not (-180 <= float(lng) <= 180):
            return jsonify({'error': 'Invalid coordinates'}), 400
        
        # Get location information
        location_data = banking_service.get_location_info(float(lat), float(lng))
        
        # Store in session for later use
        session['last_location'] = {
            'lat': float(lat),
            'lng': float(lng),
            'timestamp': datetime.now().isoformat()
        }
        
        return jsonify(location_data)
        
    except Exception as e:
        logger.error(f"Error in location-info endpoint: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/nearby-banking', methods=['GET'])
def nearby_banking():
    """Get nearby banking locations"""
    try:
        lat = request.args.get('lat', type=float)
        lng = request.args.get('lng', type=float)
        radius = request.args.get('radius', default=10.0, type=float)
        location_type = request.args.get('type', default='all')  # 'bank', 'atm', 'all'
        
        if not lat or not lng:
            return jsonify({'error': 'Latitude and longitude are required'}), 400
        
        # Find nearby locations
        nearby_locations = banking_service.find_nearby_banking(lat, lng, radius)
        
        # Filter by type if specified
        if location_type != 'all':
            nearby_locations = [loc for loc in nearby_locations if loc['type'] == location_type]
        
        return jsonify({
            'locations': nearby_locations,
            'total': len(nearby_locations),
            'search_radius': radius,
            'search_center': {'lat': lat, 'lng': lng}
        })
        
    except Exception as e:
        logger.error(f"Error in nearby-banking endpoint: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/exchange-rates', methods=['GET'])
def exchange_rates():
    """Get current exchange rates"""
    try:
        base = request.args.get('base', default='AZN')
        
        if base not in banking_service.exchange_rates:
            return jsonify({'error': 'Currency not supported'}), 400
        
        rates = banking_service.exchange_rates[base]
        
        return jsonify({
            'base_currency': base,
            'rates': rates,
            'timestamp': datetime.now().isoformat(),
            'disclaimer': 'Rates are for demonstration purposes only'
        })
        
    except Exception as e:
        logger.error(f"Error in exchange-rates endpoint: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/banking-services', methods=['GET'])
def banking_services():
    """Get available banking services in a location"""
    try:
        country = request.args.get('country')
        city = request.args.get('city')
        
        if not country:
            # Return all available locations
            result = {}
            for country_name, cities in banking_service.banking_locations.items():
                result[country_name] = list(cities.keys())
            return jsonify(result)
        
        if country not in banking_service.banking_locations:
            return jsonify({'error': 'Country not found'}), 404
        
        if not city:
            # Return cities in the country
            cities = list(banking_service.banking_locations[country].keys())
            return jsonify({country: cities})
        
        if city not in banking_service.banking_locations[country]:
            return jsonify({'error': 'City not found'}), 404
        
        # Return banking services in the city
        services = banking_service.banking_locations[country][city]
        return jsonify({
            'country': country,
            'city': city,
            'services': services,
            'total': len(services)
        })
        
    except Exception as e:
        logger.error(f"Error in banking-services endpoint: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'service': 'Banking Location Service'
    })

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
    # Get port from environment variable or default to 5000
    port = int(os.environ.get('PORT', 5001))
    
    # Run the app
    app.run(
        host='0.0.0.0',
        port=port,
        debug=os.environ.get('FLASK_ENV') == 'development'
    )