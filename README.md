# Banking Locator for Azerbaijan

A comprehensive web application for locating banking services across Azerbaijan, featuring ATMs, branches, payment terminals, and digital centers from major banks including Kapital Bank and ABB Bank.

## 🌟 Features

### 🏦 **Multi-Bank Support**
- **Kapital Bank**: ATMs, branches, payment terminals, digital centers, and cash-in machines
- **ABB Bank**: Complete branch and service locations
- Easily extensible for additional banks

### 📍 **Location Services**
- Interactive map interface for easy navigation
- GPS coordinates for precise location tracking
- Address information with detailed descriptions
- Real-time location-based search

### 🤖 **AI-Powered Assistant**
- Intelligent banking assistant powered by Google Gemini AI
- Natural language processing for user queries
- Contextual responses about banking services
- 24/7 availability for instant help

### 📱 **Progressive Web App (PWA)**
- Install as native app on mobile devices
- Offline functionality with service worker
- Fast loading and responsive design
- Native app-like experience

### 🔍 **Advanced Search & Filtering**
- Filter by bank (Kapital Bank, ABB Bank)
- Filter by service type (ATM, Branch, Payment Terminal, Digital Center, Cash-in)
- Location-based proximity search
- Real-time search results

## 🚀 Technology Stack

- **Backend**: Python Flask with Jinja2 templating
- **AI Integration**: Google Gemini 1.5 Flash API
- **Frontend**: Vanilla JavaScript, Modern CSS
- **Database**: PostgreSQL (inferred from schema)
- **PWA**: Service Worker, Web App Manifest
- **Data Sources**: Web scraping from bank APIs and websites

## 📊 Database Schema

```sql
CREATE TABLE banking_locator.locations (
    id SERIAL PRIMARY KEY,
    company VARCHAR(100) NOT NULL,           -- Bank name (e.g., 'Kapital Bank', 'ABB Bank')
    type VARCHAR(50) NOT NULL,              -- Service type (ATM, Branch, etc.)
    name VARCHAR(255) NOT NULL,             -- Location name/identifier
    address TEXT NOT NULL,                  -- Full address
    lat DECIMAL(10, 8),                     -- Latitude coordinate
    lon DECIMAL(11, 8),                     -- Longitude coordinate
    created_at TIMESTAMP DEFAULT NOW(),     -- Record creation time
    updated_at TIMESTAMP DEFAULT NOW()      -- Last update time
);
```

## 🏗️ Project Structure

```
banking_locator/
├── data/                           # Banking data storage
│   ├── abb/
│   │   └── data.json              # ABB Bank locations
│   └── kb/                        # Kapital Bank data
│       ├── atm.json               # ATM locations
│       ├── branch.json            # Branch locations  
│       ├── cashin.json            # Cash-in machines
│       ├── digitalcenter.json     # Digital centers
│       ├── paymentterminal.json   # Payment terminals
│       ├── endpoints.json         # API endpoints
│       ├── headers.json           # Request headers
│       └── kapital_bank_scraper.py # Data scraping script
├── static/                        # Static assets
│   ├── css/
│   │   └── styles.css            # Application styles
│   ├── favicon/                  # PWA icons and favicons
│   │   ├── android-icon-*.png    # Android app icons
│   │   ├── apple-icon-*.png      # iOS app icons
│   │   ├── favicon-*.png         # Browser favicons
│   │   ├── ms-icon-*.png         # Microsoft tile icons
│   │   ├── manifest.json         # PWA manifest
│   │   └── browserconfig.xml     # Browser configuration
│   └── js/
│       └── app.js               # Frontend JavaScript
├── templates/
│   └── index.html               # Main HTML template
├── .env.example                 # Environment variables template
├── LICENSE                      # MIT License
├── main.py                      # Flask application
├── requirements.txt             # Python dependencies
└── README.md                    # Project documentation
```

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- PostgreSQL database
- Google Gemini API key
- Git

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/Ismat-Samadov/banking_locator.git
   cd banking_locator
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up database**
   ```sql
   CREATE DATABASE banking_locator;
   
   CREATE TABLE banking_locator.locations (
       id SERIAL PRIMARY KEY,
       company VARCHAR(100) NOT NULL,
       type VARCHAR(50) NOT NULL,
       name VARCHAR(255) NOT NULL,
       address TEXT NOT NULL,
       lat DECIMAL(10, 8),
       lon DECIMAL(11, 8),
       created_at TIMESTAMP DEFAULT NOW(),
       updated_at TIMESTAMP DEFAULT NOW()
   );
   ```

5. **Configure environment variables**
   ```bash
   # Copy the example environment file
   cp .env.example .env
   
   # Edit .env with your actual values:
   # DB_HOST=localhost
   # DB_NAME=banking_locator
   # DB_USER=your_db_user
   # DB_PASSWORD=your_db_password
   # DB_PORT=5432
   # DB_SSLMODE=prefer
   # GEMINI_API_KEY=your-gemini-api-key-here
   # SECRET_KEY=your-secret-key-for-sessions
   # FLASK_ENV=development
   ```

6. **Load banking data**
   ```bash
   python data_loader.py  # Import JSON data to database
   ```

7. **Run the application**
   ```bash
   python main.py
   ```

8. **Open in browser**
   ```
   http://localhost:5000
   ```

## 📊 Data Management

### Kapital Bank Data Collection

The application includes a sophisticated scraper for Kapital Bank:

```python
# Example usage of the scraper
from data.kb.kapital_bank_scraper import KapitalBankScraper

scraper = KapitalBankScraper()
atm_data = scraper.get_atm_locations()
branch_data = scraper.get_branch_locations()
```

### Supported Service Types

| Service Type | Description | Banks |
|--------------|-------------|-------|
| `atm` | Automated Teller Machines | Kapital Bank |
| `branch` | Bank Branches | Kapital Bank, ABB Bank |
| `paymentterminal` | Payment Terminals | Kapital Bank |
| `digitalcenter` | Digital Service Centers | Kapital Bank |
| `cashin` | Cash Deposit Machines | Kapital Bank |

### Data Update Process

1. **Automated Scraping**: Run scrapers to collect latest data
2. **Data Validation**: Verify coordinates and address information
3. **Database Update**: Bulk insert/update location records
4. **Cache Refresh**: Update application cache for better performance

## 🗺️ API Endpoints

### Location Services

```http
GET /api/locations
```
Get all banking locations with optional filtering:
- `?company=Kapital Bank` - Filter by bank
- `?type=atm` - Filter by service type
- `?lat=40.4093&lon=49.8671&radius=5` - Search by proximity

```http
GET /api/locations/{id}
```
Get specific location details

### Banking Assistant

```http
POST /api/chat
Content-Type: application/json

{
  "message": "Where is the nearest Kapital Bank ATM?"
}
```

### Health Check

```http
GET /health
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Required | Example |
|----------|-------------|----------|---------|
| `DB_HOST` | PostgreSQL database host | Yes | `localhost` |
| `DB_NAME` | Database name | Yes | `banking_locator` |
| `DB_USER` | Database username | Yes | `postgres` |
| `DB_PASSWORD` | Database password | Yes | `your_password` |
| `DB_PORT` | Database port | Yes | `5432` |
| `DB_SSLMODE` | SSL mode for database connection | Yes | `prefer` |
| `GEMINI_API_KEY` | Google Gemini AI API key | Yes | `AIza...` |
| `SECRET_KEY` | Flask session encryption key | Yes | `your-secret-key` |
| `FLASK_ENV` | Flask environment | No | `development` |

### Setting Up Environment Variables

1. **Copy the example file**:
   ```bash
   cp .env.example .env
   ```

2. **Edit the `.env` file** with your actual values:
   ```bash
   DB_HOST=localhost
   DB_NAME=banking_locator
   DB_USER=postgres
   DB_PASSWORD=your_secure_password
   DB_PORT=5432
   DB_SSLMODE=prefer
   GEMINI_API_KEY=your_gemini_api_key_here
   SECRET_KEY=your_very_secure_secret_key
   FLASK_ENV=development
   ```

3. **For production deployment**, set these variables in your hosting platform:
   - **Render**: Add in Environment Variables section
   - **Heroku**: Use `heroku config:set`
   - **Docker**: Use environment file or docker-compose

### AI Assistant Configuration

The banking assistant uses Google Gemini with specialized prompts for banking queries:

- **Model**: `gemini-1.5-flash`
- **Context**: Azerbaijan banking system
- **Languages**: English and Azerbaijani
- **Capabilities**: Location finding, service information, general banking advice

## 🚀 Deployment

### Using Render

1. **Connect Repository**: Link your GitHub repository to Render
2. **Environment Variables**: Set all required environment variables from `.env.example`
   ```
   DB_HOST=<provided_by_render>
   DB_NAME=<provided_by_render>
   DB_USER=<provided_by_render>
   DB_PASSWORD=<provided_by_render>
   DB_PORT=5432
   DB_SSLMODE=require
   GEMINI_API_KEY=your_api_key
   SECRET_KEY=your_secret_key
   ```
3. **Build Command**: `pip install -r requirements.txt`
4. **Start Command**: `gunicorn main:app`

### Using Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "main:app"]
```

### Using Heroku

```bash
# Add Heroku PostgreSQL addon
heroku addons:create heroku-postgresql:hobby-dev

# Set environment variables
heroku config:set GEMINI_API_KEY=your_api_key
heroku config:set SECRET_KEY=your_secret_key
heroku config:set FLASK_ENV=production

# Deploy
git push heroku main
```

**Note**: Heroku automatically provides database connection variables. You may need to parse `DATABASE_URL` or set individual DB variables.

## 🧪 Testing

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-flask

# Run tests
pytest tests/

# Run with coverage
pytest --cov=main tests/
```

### Manual Testing

1. **Location Search**: Test proximity search functionality
2. **AI Assistant**: Verify responses to banking queries
3. **PWA Features**: Test offline functionality and installation
4. **Data Accuracy**: Verify location coordinates and addresses

## 🤝 Contributing

### Adding New Banks

1. **Create Data Directory**: `data/[bank_abbreviation]/`
2. **Implement Scraper**: Following the Kapital Bank scraper pattern
3. **Add to Database**: Update location table with new bank data
4. **Update Frontend**: Add bank to filtering options

### Data Collection Guidelines

- Always respect `robots.txt` and rate limits
- Verify location accuracy with multiple sources
- Include proper error handling and retry logic
- Document API endpoints and response formats

### Code Style

- Follow PEP 8 for Python code
- Use meaningful variable and function names
- Add docstrings for all functions and classes
- Include type hints where appropriate

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

### Common Issues

1. **Database Connection**: Ensure PostgreSQL is running and credentials are correct
2. **API Limits**: Monitor Google Gemini API usage and rate limits
3. **Scraping Failures**: Check if bank websites have changed their structure

### Getting Help

- Create an issue on GitHub for bugs or feature requests
- Check existing issues for solutions
- Review the documentation for API usage

## 🙏 Acknowledgments

- **Banks**: Kapital Bank and ABB Bank for providing accessible location data
- **Google Gemini**: For powering the AI assistant capabilities
- **OpenStreetMap**: For geographical data validation
- **Flask Community**: For the excellent web framework

## 📊 Statistics

- **Banks Supported**: 2 (Kapital Bank, ABB Bank)
- **Service Types**: 5 (ATM, Branch, Payment Terminal, Digital Center, Cash-in)
- **Locations**: 500+ banking locations across Azerbaijan
- **Coverage**: Major cities and regions in Azerbaijan

---

**Note**: This project is independent and not officially affiliated with any banking institution. Always verify banking information with official bank sources for the most current details.