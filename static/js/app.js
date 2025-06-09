// Global variables
let map;
let userLocation = null;
let markersLayer;
let userMarker;
let currentLocations = [];
let locationMarkers = {}; // Store markers by location ID

console.log("🚀 Banking Locator App JavaScript loaded!");
console.log("Current URL:", window.location.href);
console.log("User Agent:", navigator.userAgent);

// Icons for different service types
const serviceIcons = {
    'atm': '🏧',
    'branch': '🏦',
    'digital': '💻',
    'cashin': '💰',
    'terminal': '🖥️',
    'default': '📍'
};

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM Content Loaded - App starting...');
    
    // Add a visible indicator that JavaScript is working
    const statusElement = document.getElementById('status');
    if (statusElement) {
        statusElement.innerHTML = 'JavaScript loaded successfully! Checking components...';
        statusElement.className = 'status success';
    }
    
    // Check if all required elements exist
    const requiredElements = ['map', 'findNearby', 'refreshLocation', 'serviceType', 'radius', 'status'];
    const missingElements = [];
    
    requiredElements.forEach(id => {
        const element = document.getElementById(id);
        if (!element) {
            missingElements.push(id);
            console.error(`❌ Missing element: ${id}`);
        } else {
            console.log(`✅ Found element: ${id}`);
        }
    });
    
    if (missingElements.length > 0) {
        console.error('Missing required elements:', missingElements);
        const statusElement = document.getElementById('status');
        if (statusElement) {
            statusElement.innerHTML = 'ERROR: Missing page elements: ' + missingElements.join(', ');
            statusElement.className = 'status error';
        }
        return;
    }
    
    // Check if Leaflet is loaded
    if (typeof L === 'undefined') {
        console.error('Leaflet library not loaded');
        const statusElement = document.getElementById('status');
        if (statusElement) {
            statusElement.innerHTML = 'ERROR: Leaflet map library failed to load. Check your internet connection.';
            statusElement.className = 'status error';
        }
        return;
    }
    
    console.log('✅ All required elements found, initializing...');
    
    try {
        initializeMap();
        loadServiceTypes();
        setupEventListeners();
        setupMapClickHandler();
        
        // Auto-request location on load
        setTimeout(() => {
            requestLocation();
        }, 1000);
        
        console.log('✅ Initialization complete');
        updateStatus('Application loaded successfully! Requesting your location...', 'loading');
        
    } catch (error) {
        console.error('❌ Error during initialization:', error);
        updateStatus('Error initializing application: ' + error.message, 'error');
    }
});

// Initialize Leaflet map
function initializeMap() {
    console.log('Initializing map...');
    
    try {
        map = L.map('map').setView([40.4093, 49.8671], 12); // Default to Baku, Azerbaijan
        console.log('Map created successfully');
        
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors'
        }).addTo(map);
        console.log('Tile layer added');
        
        markersLayer = L.layerGroup().addTo(map);
        console.log('Markers layer added');
        
        // Test if map is working
        map.on('click', function(e) {
            console.log('Map clicked at:', e.latlng);
        });
        
    } catch (error) {
        console.error('Error initializing map:', error);
        updateStatus('Error initializing map: ' + error.message, 'error');
    }
}

// Update status message
function updateStatus(message, type = '') {
    const statusElement = document.getElementById('status');
    if (statusElement) {
        statusElement.textContent = message;
        statusElement.className = 'status ' + type;
    }
    console.log('Status updated:', message, type);
}

// Show/hide loading overlay
function showLoading(show) {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
        if (show) {
            overlay.classList.add('show');
        } else {
            overlay.classList.remove('show');
        }
    }
}

// Handle map click to manually set location (fallback)
function setupMapClickHandler() {
    if (map) {
        map.on('click', function(e) {
            console.log('Map clicked at:', e.latlng);
            if (!userLocation) {
                userLocation = {
                    lat: e.latlng.lat,
                    lng: e.latlng.lng
                };
                updateUserMarker();
                updateStatus('Location set manually. Click "Find Nearby Services" to search', 'success');
                console.log('User location set via map click:', userLocation);
            }
        });
        console.log('✅ Map click handler setup complete');
    } else {
        console.error('❌ Cannot setup map click handler - map not initialized');
    }
}

// Load available service types
async function loadServiceTypes() {
    console.log('Loading service types...');
    try {
        const response = await fetch('/api/location-types');
        const data = await response.json();
        
        if (data.success) {
            const select = document.getElementById('serviceType');
            data.types.forEach(type => {
                const option = document.createElement('option');
                option.value = type;
                option.textContent = type.charAt(0).toUpperCase() + type.slice(1);
                select.appendChild(option);
            });
            console.log('✅ Service types loaded:', data.types);
        } else {
            console.error('❌ Failed to load service types:', data);
        }
    } catch (error) {
        console.error('❌ Error loading service types:', error);
    }
}

// Setup event listeners
function setupEventListeners() {
    console.log('Setting up event listeners...');
    
    const findButton = document.getElementById('findNearby');
    const refreshButton = document.getElementById('refreshLocation');
    const testButton = document.getElementById('testButton');
    const serviceSelect = document.getElementById('serviceType');
    const radiusSelect = document.getElementById('radius');
    
    if (findButton) {
        findButton.addEventListener('click', function(e) {
            console.log('Find Nearby button clicked');
            e.preventDefault();
            findNearbyServices();
        });
        console.log('✓ Find button listener added');
    } else {
        console.error('Find button not found');
    }
    
    if (refreshButton) {
        refreshButton.addEventListener('click', function(e) {
            console.log('Refresh Location button clicked');
            e.preventDefault();
            requestLocation();
        });
        console.log('✓ Refresh button listener added');
    } else {
        console.error('Refresh button not found');
    }
    
    if (testButton) {
        testButton.addEventListener('click', function(e) {
            console.log('Test button clicked');
            e.preventDefault();
            testApplication();
        });
        console.log('✓ Test button listener added');
    } else {
        console.error('Test button not found');
    }
    
    if (serviceSelect) {
        serviceSelect.addEventListener('change', function(e) {
            console.log('Service type changed to:', e.target.value);
            filterCurrentResults();
        });
        console.log('✓ Service select listener added');
    } else {
        console.error('Service select not found');
    }
    
    if (radiusSelect) {
        radiusSelect.addEventListener('change', function(e) {
            console.log('Radius changed to:', e.target.value);
            if (userLocation && currentLocations.length > 0) {
                findNearbyServices();
            }
        });
        console.log('✓ Radius select listener added');
    } else {
        console.error('Radius select not found');
    }
}

// Request user's geolocation
function requestLocation() {
    console.log('requestLocation called');
    updateStatus('Requesting your location...', 'loading');
    
    if (!navigator.geolocation) {
        console.log('Geolocation not supported');
        updateStatus('Geolocation is not supported by your browser', 'error');
        return;
    }
    
    console.log('Requesting geolocation...');
    navigator.geolocation.getCurrentPosition(
        (position) => {
            console.log('Geolocation success:', position);
            userLocation = {
                lat: position.coords.latitude,
                lng: position.coords.longitude
            };
            
            console.log('User location set:', userLocation);
            updateStatus('Location found! Click "Find Nearby Services" to search', 'success');
            updateUserMarker();
            map.setView([userLocation.lat, userLocation.lng], 14);
        },
        (error) => {
            console.log('Geolocation error:', error);
            let errorMessage = 'Unable to get your location. ';
            switch(error.code) {
                case error.PERMISSION_DENIED:
                    errorMessage += 'Please allow location access and try again.';
                    break;
                case error.POSITION_UNAVAILABLE:
                    errorMessage += 'Location information unavailable.';
                    break;
                case error.TIMEOUT:
                    errorMessage += 'Location request timed out.';
                    break;
                default:
                    errorMessage += 'An unknown error occurred.';
                    break;
            }
            updateStatus(errorMessage, 'error');
            
            // Fallback: Set location to Baku, Azerbaijan (based on your .env location)
            console.log('Setting fallback location to Baku');
            userLocation = {
                lat: 40.4093,
                lng: 49.8671
            };
            updateUserMarker();
            updateStatus('Using default location (Baku). Click on map to set your location manually.', 'success');
        },
        {
            enableHighAccuracy: true,
            timeout: 10000,
            maximumAge: 60000
        }
    );
}

// Update user marker on map
function updateUserMarker() {
    if (userMarker) {
        map.removeLayer(userMarker);
    }
    
    if (userLocation) {
        const userIcon = L.divIcon({
            html: '<div style="background: #667eea; width: 20px; height: 20px; border-radius: 50%; border: 3px solid white; box-shadow: 0 2px 10px rgba(0,0,0,0.3);"></div>',
            iconSize: [20, 20],
            className: 'user-location-marker'
        });
        
        userMarker = L.marker([userLocation.lat, userLocation.lng], { icon: userIcon })
            .addTo(map)
            .bindPopup('<div class="popup-header">📍 Your Location</div>');
    }
}

// Find nearby services
async function findNearbyServices() {
    console.log('findNearbyServices called');
    console.log('userLocation:', userLocation);
    
    if (!userLocation) {
        updateStatus('Please allow location access first', 'error');
        requestLocation();
        return;
    }
    
    const serviceType = document.getElementById('serviceType').value;
    const radius = parseFloat(document.getElementById('radius').value);
    
    console.log('Service type:', serviceType);
    console.log('Radius:', radius);
    
    showLoading(true);
    updateStatus('Searching for nearby services...', 'loading');
    
    try {
        const requestBody = {
            latitude: userLocation.lat,
            longitude: userLocation.lng,
            radius: radius,
            type: serviceType,
            limit: 50
        };
        
        console.log('Request body:', requestBody);
        
        const response = await fetch('/api/nearby-locations', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestBody)
        });
        
        console.log('Response status:', response.status);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('Response data:', data);
        
        if (data.success) {
            currentLocations = data.locations;
            displayResults(currentLocations);
            displayMarkersOnMap(currentLocations);
            updateStatus(`Found ${data.count} services within ${radius}km`, 'success');
        } else {
            updateStatus(data.error || 'Error searching for services', 'error');
        }
    } catch (error) {
        console.error('Error finding nearby services:', error);
        updateStatus('Error connecting to server: ' + error.message, 'error');
    } finally {
        showLoading(false);
    }
}

// Filter current results by service type
function filterCurrentResults() {
    const serviceType = document.getElementById('serviceType').value;
    
    if (currentLocations.length === 0) {
        return;
    }
    
    let filteredLocations;
    if (serviceType === 'all') {
        filteredLocations = currentLocations;
    } else {
        filteredLocations = currentLocations.filter(location => location.type === serviceType);
    }
    
    displayResults(filteredLocations);
    displayMarkersOnMap(filteredLocations);
    
    const radius = document.getElementById('radius').value;
    updateStatus(`Found ${filteredLocations.length} services within ${radius}km`, 'success');
}

// Display results in the results panel
function displayResults(locations) {
    const resultsContainer = document.getElementById('results');
    const resultsCount = document.getElementById('resultsCount');
    
    resultsCount.textContent = `${locations.length} locations found`;
    
    if (locations.length === 0) {
        resultsContainer.innerHTML = '<div class="no-results">No services found. Try adjusting your search radius or service type.</div>';
        return;
    }
    
    const resultsHTML = locations.map(location => {
        const icon = serviceIcons[location.type] || serviceIcons.default;
        return `
            <div class="location-card" data-id="${location.id}" onclick="selectLocation(${location.id}, ${location.lat}, ${location.lon})">
                <div class="location-header">
                    <div class="location-name">${icon} ${location.name || 'Unnamed Location'}</div>
                    <div class="location-distance">${location.distance} km</div>
                </div>
                <div class="location-company">${location.company || 'Unknown Company'}</div>
                <div class="location-type">${location.type || 'Unknown Type'}</div>
                <div class="location-address">${location.address || 'No address available'}</div>
            </div>
        `;
    }).join('');
    
    resultsContainer.innerHTML = resultsHTML;
    console.log('✅ Displayed', locations.length, 'results in panel');
}

// Display markers on map
function displayMarkersOnMap(locations) {
    // Clear existing markers
    markersLayer.clearLayers();
    locationMarkers = {}; // Clear marker references
    
    locations.forEach(location => {
        const icon = serviceIcons[location.type] || serviceIcons.default;
        
        const customIcon = L.divIcon({
            html: `<div style="background: white; border: 2px solid #667eea; border-radius: 50%; width: 30px; height: 30px; display: flex; align-items: center; justify-content: center; font-size: 14px; box-shadow: 0 2px 10px rgba(0,0,0,0.3);">${icon}</div>`,
            iconSize: [30, 30],
            className: 'custom-marker'
        });
        
        const marker = L.marker([location.lat, location.lon], { icon: customIcon })
            .bindPopup(`
                <div class="custom-popup">
                    <div class="popup-header">${location.name || 'Unnamed Location'}</div>
                    <div class="popup-company">${location.company || 'Unknown Company'}</div>
                    <div class="popup-type">${location.type || 'Unknown Type'}</div>
                    <div class="popup-address">${location.address || 'No address available'}</div>
                    <div style="margin-top: 8px; font-weight: 600; color: #667eea;">📍 ${location.distance} km away</div>
                </div>
            `);
        
        // Store marker reference by location ID
        locationMarkers[location.id] = marker;
        markersLayer.addLayer(marker);
    });
    
    // Fit map to show all markers and user location
    if (locations.length > 0 && userLocation && userMarker) {
        try {
            const group = new L.featureGroup([markersLayer, userMarker]);
            map.fitBounds(group.getBounds().pad(0.1));
        } catch (error) {
            console.log('Could not fit bounds, using default view');
            map.setView([userLocation.lat, userLocation.lng], 12);
        }
    }
    
    console.log('✅ Displayed', locations.length, 'markers on map');
}