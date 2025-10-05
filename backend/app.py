from flask import Flask, send_file, jsonify, request, abort
from flask_cors import CORS
import os
import hashlib
import google.generativeai as genai
import json
import sqlite3

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend requests

# Configuration
TILES_BASE_DIR = "tiles"  # Directory where tiles are stored
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY"  # Replace with your API key
DB_PATH = "locations.db"

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')  # Updated model name


# Database setup
def init_db():
    """Initialize SQLite database with locations table"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            lat REAL NOT NULL,
            lng REAL NOT NULL,
            zoom INTEGER NOT NULL,
            description TEXT,
            planet TEXT DEFAULT 'Mars',
            category TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()


def get_all_locations():
    """Get all locations from database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT name, lat, lng, zoom, description, planet, category FROM locations')
    locations = cursor.fetchall()
    
    conn.close()
    
    return [
        {
            "name": loc[0],
            "lat": loc[1],
            "lng": loc[2],
            "zoom": loc[3],
            "description": loc[4],
            "planet": loc[5],
            "category": loc[6]
        }
        for loc in locations
    ]


def add_location(name, lat, lng, zoom, description="", planet="Mars", category=""):
    """Add a new location to database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO locations (name, lat, lng, zoom, description, planet, category)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (name, lat, lng, zoom, description, planet, category))
        
        conn.commit()
        location_id = cursor.lastrowid
        conn.close()
        return location_id
    except sqlite3.IntegrityError:
        conn.close()
        return None


def seed_sample_locations():
    """Add sample Mars locations if database is empty"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM locations')
    count = cursor.fetchone()[0]
    
    if count == 0:
        sample_locations = [
            ("Olympus Mons", 18.65, -133.8, 10, "Largest volcano in the solar system", "Mars", "volcano"),
            ("Valles Marineris", -14.0, -59.2, 8, "Massive canyon system", "Mars", "canyon"),
            ("Gale Crater", -5.4, 137.8, 12, "Curiosity rover landing site", "Mars", "crater"),
            ("Jezero Crater", 18.38, 77.58, 12, "Perseverance rover landing site", "Mars", "crater"),
            ("Hellas Basin", -42.4, 70.5, 7, "Deepest impact crater on Mars", "Mars", "basin"),
            ("Tharsis Region", 2.5, -112.5, 6, "Volcanic plateau region", "Mars", "region"),
            ("Elysium Mons", 25.0, 147.0, 10, "Second largest volcano on Mars", "Mars", "volcano"),
            ("Utopia Planitia", 50.0, 110.0, 5, "Large plain in northern hemisphere", "Mars", "plain"),
            ("Argyre Basin", -49.7, -43.4, 7, "Large impact basin", "Mars", "basin"),
            ("Noctis Labyrinthus", -7.0, -101.5, 11, "Complex maze of canyons", "Mars", "canyon")
        ]
        
        cursor.executemany('''
            INSERT INTO locations (name, lat, lng, zoom, description, planet, category)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', sample_locations)
        
        conn.commit()
        print(f"Added {len(sample_locations)} sample locations to database")
    
    conn.close()


# Initialize database on startup
init_db()
seed_sample_locations()


@app.route('/tiles/<int:z>/<int:x>/<int:y>.<ext>')
def get_tile(z, x, y, ext):
    """
    Serve tile images
    URL format: /tiles/{z}/{x}/{y}.png
    """
    # Validate extension
    if ext not in ['png', 'jpg', 'jpeg']:
        abort(400, "Invalid tile format")
    
    # Build file path
    tile_path = os.path.join(TILES_BASE_DIR, str(z), str(x), f"{y}.{ext}")
    
    # Check if tile exists
    if not os.path.exists(tile_path):
        abort(404, "Tile not found")
    
    # Generate ETag for caching
    file_stat = os.stat(tile_path)
    etag = hashlib.md5(f"{tile_path}{file_stat.st_mtime}".encode()).hexdigest()
    
    # Check If-None-Match header for caching
    if request.headers.get('If-None-Match') == etag:
        return '', 304  # Not Modified
    
    # Serve the tile with caching headers
    response = send_file(
        tile_path,
        mimetype=f'image/{ext}',
        conditional=True
    )
    
    # Set caching headers (24 hours)
    response.headers['Cache-Control'] = 'public, max-age=86400'
    response.headers['ETag'] = etag
    
    return response


@app.route('/search', methods=['POST'])
def search_location():
    """
    Search for a location using Gemini AI with database context
    Expects JSON: {"query": "Olympus Mons on Mars"}
    Returns: {"lat": 18.65, "lng": -133.8, "zoom": 10, "name": "Olympus Mons"}
    """
    try:
        data = request.get_json()
        query = data.get('query', '')
        
        if not query:
            abort(400, "Query is required")
        
        # Get all available locations from database
        available_locations = get_all_locations()
        
        # Create context for Gemini
        locations_context = "\n".join([
            f"- {loc['name']}: lat={loc['lat']}, lng={loc['lng']}, zoom={loc['zoom']}, "
            f"description={loc['description']}, planet={loc['planet']}, category={loc['category']}"
            for loc in available_locations
        ])
        
        # Create prompt for Gemini with database context
        prompt = f"""You are a location search assistant. You have access to the following locations in the database:

{locations_context}

User query: "{query}"

Your task:
1. Match the user's query to the MOST RELEVANT location from the database above
2. Consider synonyms, descriptions, and partial matches
3. If query mentions specific features (volcano, crater, rover, etc.), prioritize by category

Respond ONLY with valid JSON in this exact format (no markdown, no extra text):
{{
    "name": "<exact name from database>",
    "lat": <latitude>,
    "lng": <longitude>,
    "zoom": <zoom level>,
    "description": "<description from database>",
    "match_confidence": "<high/medium/low>"
}}

If NO good match found, return:
{{"error": "Location not found in database", "suggestion": "Try: [list 2-3 closest matches]"}}

Examples:
- "biggest volcano" -> Match to "Olympus Mons" (category: volcano)
- "curiosity landing" -> Match to "Gale Crater" (description mentions Curiosity)
- "deep crater" -> Match to "Hellas Basin" (deepest crater)
- "canyon system" -> Match to "Valles Marineris" (category: canyon)"""
        
        # Get response from Gemini
        response = model.generate_content(prompt)
        response_text = response.text.strip()
        
        # Clean up markdown formatting
        if response_text.startswith('```'):
            response_text = response_text.split('```')[1]
            if response_text.startswith('json'):
                response_text = response_text[4:]
        response_text = response_text.strip()
        
        # Parse JSON response
        location_data = json.loads(response_text)
        
        # Check if location was found
        if 'error' in location_data:
            return jsonify({
                "status": "error",
                "message": location_data['error'],
                "suggestion": location_data.get('suggestion', '')
            }), 404
        
        return jsonify({
            "status": "success",
            "location": location_data
        })
        
    except json.JSONDecodeError as e:
        return jsonify({
            "status": "error",
            "message": f"Failed to parse location data: {str(e)}",
            "raw_response": response_text if 'response_text' in locals() else None
        }), 500
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Search failed: {str(e)}"
        }), 500


@app.route('/locations', methods=['GET'])
def list_locations():
    """
    List all available locations in the database
    """
    try:
        locations = get_all_locations()
        return jsonify({
            "status": "success",
            "count": len(locations),
            "locations": locations
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route('/locations', methods=['POST'])
def create_location():
    """
    Add a new location to the database
    Expects JSON: {
        "name": "Location Name",
        "lat": 10.5,
        "lng": -120.3,
        "zoom": 10,
        "description": "Optional description",
        "planet": "Mars",
        "category": "crater"
    }
    """
    try:
        data = request.get_json()
        
        required_fields = ['name', 'lat', 'lng', 'zoom']
        for field in required_fields:
            if field not in data:
                abort(400, f"Missing required field: {field}")
        
        location_id = add_location(
            name=data['name'],
            lat=data['lat'],
            lng=data['lng'],
            zoom=data['zoom'],
            description=data.get('description', ''),
            planet=data.get('planet', 'Mars'),
            category=data.get('category', '')
        )
        
        if location_id is None:
            return jsonify({
                "status": "error",
                "message": "Location already exists"
            }), 409
        
        return jsonify({
            "status": "success",
            "message": "Location added successfully",
            "id": location_id
        }), 201
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route('/health')
def health_check():
    """
    Health check endpoint
    """
    return jsonify({
        "status": "healthy",
        "tiles_directory": os.path.exists(TILES_BASE_DIR)
    })


@app.route('/')
def index():
    """
    API info
    """
    return jsonify({
        "name": "Tile Server API with Smart Search",
        "endpoints": {
            "GET /tiles/{z}/{x}/{y}.png": "Get tile image",
            "POST /search": "Search location (send JSON: {\"query\": \"location name\"})",
            "GET /locations": "List all available locations",
            "POST /locations": "Add new location to database"
        }
    })


# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "status": "error",
        "message": "Tile not found"
    }), 404


@app.errorhandler(400)
def bad_request(error):
    return jsonify({
        "status": "error",
        "message": str(error)
    }), 400


if __name__ == '__main__':
    # Create tiles directory if it doesn't exist
    os.makedirs(TILES_BASE_DIR, exist_ok=True)
    
    # Run the server
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    )