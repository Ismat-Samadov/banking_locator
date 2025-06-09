# 🏦 Banking Locator Web App

A geospatial web application that detects the user's real-time location and compares it to a dataset of nearby bank branches. The application returns the closest branches across multiple banks, with distances, map visualization, and optional filtering by services.

---

## 📌 Features

* 🧭 Detects user’s current location via GPS (HTML5 Geolocation API)
* 🗺️ Visualizes bank branches on an interactive map (Mapbox/Leaflet)
* 📍 Displays nearest branches from different banks, sorted by distance
* 📊 Optionally shows service availability (ATM, loans, currency exchange, etc.)
* 📱 Responsive and PWA-ready (offline support planned)
* 🔐 Built with privacy in mind — no persistent user tracking

---

## 🗂️ Project Structure

```bash
.
├── data
│   ├── extract.ipynb         # Notebook to parse/scrape/import branch data
│   └── placeholder.json      # Sample coordinates of branches (GeoJSON or list)
├── LICENSE
├── main.py                   # Flask backend server
├── README.md                 # This file
├── requirements.txt          # Python dependencies
├── static
│   ├── css/styles.css        # App styling
│   └── js/app.js             # Frontend JavaScript logic (map, geolocation, fetch)
└── templates
    └── index.html            # Main UI layout (rendered via Jinja2)
```

---

## ⚙️ Tech Stack

| Layer       | Technology                          |
| ----------- | ----------------------------------- |
| Backend     | Python 3.12, Flask                  |
| Frontend    | HTML5, CSS, JavaScript              |
| Map API     | Leaflet.js + OpenStreetMap          |
| Geolocation | HTML5 Navigator API                 |
| Data Format | GeoJSON or JSON                     |
| DB (future) | Postgres + PostGIS (TBD)            |
| Hosting     | Render / Railway / Heroku (planned) |

---

## 🚀 Installation & Running Locally

### 1. Clone the repository

```bash
git clone https://github.com/Ismat-Samadov/banking_locator.git
cd banking_locator
```

### 2. Create and activate virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the server

```bash
python main.py
```

Open your browser and go to: [http://127.0.0.1:5000](http://127.0.0.1:5000)

---

## 🧭 Application Flow

1. **User opens the app** → prompts for location access.
2. **User location is captured** via the browser’s GPS (or IP-based fallback).
3. **Frontend sends coordinates to backend** (`/nearest` endpoint).
4. **Backend loads all branch coordinates** from `placeholder.json`.
5. **Distance between user and each branch** is calculated using Haversine formula.
6. **Branches are sorted by proximity** and returned as JSON.
7. **Frontend renders** map markers and list view with distances.
8. **User can click on branches** to get direction links via Google Maps.

---

## 📐 API Design

### `GET /`

* Renders `index.html`

### `POST /nearest`

* Accepts:

  ```json
  {
    "latitude": 40.4093,
    "longitude": 49.8671
  }
  ```
* Returns:

  ```json
  [
    {
      "bank_name": "Kapital Bank",
      "branch_name": "Nizami",
      "lat": 40.3777,
      "lon": 49.892,
      "distance_km": 2.14
    },
    ...
  ]
  ```

---

## 📁 Data Format (placeholder.json)

```json
[
  {
    "bank_name": "Kapital Bank",
    "branch_name": "Nizami",
    "latitude": 40.3777,
    "longitude": 49.8920
  },
  {
    "bank_name": "International Bank",
    "branch_name": "28 May",
    "latitude": 40.3783,
    "longitude": 49.8462
  }
]
```

Future enhancement: Replace with PostGIS DB for optimized spatial queries.

---

## 📊 Future Roadmap

### 🔹 Phase 1: MVP (Complete)

* [x] User location detection
* [x] Load static bank data from JSON
* [x] Haversine distance calculation
* [x] Nearest branches endpoint
* [x] Map + list UI

### 🔹 Phase 2: Extended Functionality

* [ ] Filter branches by bank or services
* [ ] Operating hours display
* [ ] Google Maps directions link
* [ ] Heatmap of branch density

### 🔹 Phase 3: Performance and UX

* [ ] Convert to PWA (offline access, caching)
* [ ] Backend caching for common queries
* [ ] Paginated results
* [ ] Multilingual support (AZ, EN, RU)

### 🔹 Phase 4: Database + Admin Tools

* [ ] Migrate to PostgreSQL + PostGIS
* [ ] Admin dashboard for uploading new branch data
* [ ] Cron jobs for scraping latest data

---

## 🛡️ Privacy Considerations

* Location is only used temporarily during session
* No data is stored or logged persistently
* GPS request explicitly prompted from browser
* Optional “manual location input” for users who deny permission

---

## 💡 Example Use Cases

* Bank comparison for customer branch proximity
* ATM location tool for mobile banking apps
* Competitive analysis for bank expansions
* Emergency locator for nearest financial services

---

## 🤝 Contributing

1. Fork the repo
2. Create a branch (`git checkout -b feature/something`)
3. Commit changes (`git commit -am 'add feature'`)
4. Push and create PR

---

## 📄 License

MIT License © 2025 [Ismat Samadov](https://github.com/Ismat-Samadov)

---

## 📬 Contact

For questions or collaborations:

* GitHub: [@Ismat-Samadov](https://github.com/Ismat-Samadov)
* Email: `your.email@example.com`

